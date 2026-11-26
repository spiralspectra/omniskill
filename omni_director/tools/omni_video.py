"""Gemini Omni 1.1 Video and Multimodal Audio Engine."""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from omni_director.config import DirectorConfig
from omni_director.schemas import MasterProductionBible, ScenePromptSpec, StorytellingMode
from omni_director.tools.prompt_auditor import compile_clean_omni_prompt


def _deterministic_scene_seed(scene: ScenePromptSpec, take_tag: str = "") -> int:
    prompt_text = (
        str(getattr(scene, "omni_prose_prompt", "") or "").strip()
        or str(getattr(scene, "scene_title", f"Scene {scene.scene_index}") or f"Scene {scene.scene_index}")
    )
    digest = hashlib.sha256(f"{prompt_text}:{scene.scene_index}:{take_tag}".encode("utf-8")).hexdigest()[:8]
    return (int(digest, 16) % 2_147_483_646) + 1


class GeminiOmniVideoEngine:
    """Video and synchronized diegetic audio generation engine powered by Gemini Omni 1.1.

    Invokes `client.interactions.create(model=config.video_model, ...)` with native
    support for:
    - Mode A: Parallel multi-scene cuts binding up to 3 Nano Banana reference images
    - Mode B: Sequential +10s scene extensions chaining previous_interaction_id up to 40s
    - Dry-run simulation for instant zero-credit verification
    """

    def __init__(self, config: Optional[DirectorConfig] = None):
        self.config = config or DirectorConfig()

    def _resolve_scene_render_params(
        self,
        scene: ScenePromptSpec,
        bible: MasterProductionBible,
        promote_take: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        """Resolves seed, selected_take_id, end_frame_path, and previous_interaction_id."""
        sc_idx = int(getattr(scene, "scene_index", 1) or 1)
        job_spec = getattr(scene, "render_job_spec", None)
        if job_spec is None:
            master_jobs = getattr(bible, "master_render_jobs", None)
            for job in list(getattr(master_jobs, "jobs", None) or []):
                if int(getattr(job, "scene_index", 0) or 0) == sc_idx:
                    job_spec = job
                    break

        promoted_override = (promote_take or {}).get(sc_idx)
        selected_take_id: Optional[str] = None
        seed: Optional[int] = None

        if promoted_override:
            selected_take_id = str(promoted_override)
            if job_spec is not None:
                for sc in list(getattr(job_spec, "take_scorecards", None) or []):
                    if getattr(sc, "take_id", None) == selected_take_id:
                        seed = int(sc.seed)
                        break
            if seed is None:
                comp_spec = getattr(scene, "compute_estimate_spec", None)
                for tv in list(getattr(comp_spec, "takes", None) or []):
                    if getattr(tv, "take_id", None) == selected_take_id:
                        seed = int(tv.seed)
                        break
            if seed is None:
                seed = _deterministic_scene_seed(scene, take_tag=selected_take_id)
        elif job_spec is not None:
            selected_take_id = str(job_spec.selected_take_id)
            seed = int(job_spec.seed)
        else:
            selected_take_id = f"SC{sc_idx:02d}_T1"
            seed = _deterministic_scene_seed(scene, take_tag=selected_take_id)

        end_frame_path = (
            str(getattr(job_spec, "end_frame_path", "") or "")
            if job_spec is not None
            else ""
        ) or f"End_Frame_{sc_idx:02d}.png"
        prev_inter_override = (
            getattr(job_spec, "previous_interaction_id", None)
            if job_spec is not None
            else None
        )
        return {
            "seed": seed,
            "selected_take_id": selected_take_id,
            "end_frame_path": end_frame_path,
            "previous_interaction_id": prev_inter_override,
        }

    def render_production_scenes(
        self,
        bible: MasterProductionBible,
        reference_plate_paths: Optional[Dict[str, str]] = None,
        scene_filter: Optional[List[int]] = None,
        promote_take: Optional[Dict[int, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Renders video scenes according to the MasterProductionBible and storytelling mode."""
        if not self.config.dry_run:
            client_review = getattr(bible, "master_client_review", None) or getattr(bible, "client_review", None)
            if client_review is not None and getattr(client_review, "ready_for_live_render", True) is False:
                scenes = [
                    s for s in list(getattr(bible, "scenes", None) or [])
                    if scene_filter is None or s.scene_index in scene_filter
                ]
                if not scenes:
                    return [{
                        "scene_index": 0,
                        "status": "blocked_by_client_review",
                        "reason": "Client review signoff gate not cleared (ready_for_live_render=False).",
                    }]
                return [
                    {
                        "scene_index": scene.scene_index,
                        "scene_title": scene.scene_title,
                        "status": "blocked_by_client_review",
                        "reason": "Client review signoff gate not cleared (ready_for_live_render=False).",
                    }
                    for scene in scenes
                ]

        if self.config.dry_run or not self.config.api_key:
            return self._simulate_dry_run_render(
                bible,
                reference_plate_paths,
                scene_filter=scene_filter,
                promote_take=promote_take,
            )

        return self._execute_live_omni_render(
            bible,
            reference_plate_paths,
            scene_filter=scene_filter,
            promote_take=promote_take,
        )

    def _simulate_dry_run_render(
        self,
        bible: MasterProductionBible,
        reference_plate_paths: Optional[Dict[str, str]] = None,
        scene_filter: Optional[List[int]] = None,
        promote_take: Optional[Dict[int, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Simulates Omni 1.1 video interaction calls in dry-run mode."""
        results: List[Dict[str, Any]] = []
        prev_interaction_id: Optional[str] = None
        is_mode_b = bible.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN

        for scene in bible.scenes:
            params = self._resolve_scene_render_params(scene, bible, promote_take=promote_take)
            seed = int(params["seed"])
            interaction_id = f"omni-interact-{scene.scene_index}-{seed % 100000:05d}"
            effective_prev_id = prev_interaction_id or params["previous_interaction_id"]

            if scene_filter is not None and scene.scene_index not in scene_filter:
                if is_mode_b:
                    prev_interaction_id = interaction_id
                continue

            bound_references = []
            if reference_plate_paths:
                for tag, path in reference_plate_paths.items():
                    if tag.startswith("<image_"):
                        bound_references.append({"tag": tag, "source": path})

            record: Dict[str, Any] = {
                "scene_index": scene.scene_index,
                "scene_title": scene.scene_title,
                "timestamp_range": scene.timestamp_range,
                "interaction_id": interaction_id,
                "status": "dry-run-completed",
                "model": self.config.video_model,
                "resolution": "720p",
                "fps": 24,
                "mode": bible.storytelling_mode.value,
                "seed": seed,
                "selected_take_id": params["selected_take_id"],
                "end_frame_path": params["end_frame_path"],
                "bound_references": bound_references[:3],
                "clean_prose_prompt": compile_clean_omni_prompt(scene.omni_prose_prompt),
                "diegetic_audio_synced": True,
                "mock_video_url": f"file:///outputs/rendered_scene_{scene.scene_index}.mp4"
            }

            if is_mode_b:
                record["previous_interaction_id"] = effective_prev_id
                prev_interaction_id = interaction_id

            results.append(record)

        return results

    def _execute_live_omni_render(
        self,
        bible: MasterProductionBible,
        reference_plate_paths: Optional[Dict[str, str]] = None,
        scene_filter: Optional[List[int]] = None,
        promote_take: Optional[Dict[int, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Invokes Google GenAI SDK client.interactions.create for live video generation."""
        try:
            from google import genai
            client = genai.Client(api_key=self.config.api_key)
        except Exception:
            # Fall back gracefully to simulation if SDK connection fails
            return self._simulate_dry_run_render(
                bible,
                reference_plate_paths,
                scene_filter=scene_filter,
                promote_take=promote_take,
            )

        results: List[Dict[str, Any]] = []
        prev_interaction_id: Optional[str] = None
        is_mode_b = bible.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN

        for scene in bible.scenes:
            params = self._resolve_scene_render_params(scene, bible, promote_take=promote_take)
            seed = int(params["seed"])
            effective_prev_id = prev_interaction_id or params["previous_interaction_id"]

            if scene_filter is not None and scene.scene_index not in scene_filter:
                if is_mode_b:
                    prev_interaction_id = f"omni-interact-{scene.scene_index}-{seed % 100000:05d}"
                continue

            try:
                bound_references: List[Dict[str, str]] = []
                contents: List[Any] = []
                if reference_plate_paths:
                    from google.genai import types
                    for tag in ["<image_1>", "<image_2>", "<image_3>"]:
                        path_str = reference_plate_paths.get(tag)
                        if path_str and Path(path_str).exists():
                            ref_path = Path(path_str)
                            mime = "image/svg+xml" if ref_path.suffix == ".svg" else "image/png"
                            part = types.Part.from_bytes(data=ref_path.read_bytes(), mime_type=mime)
                            contents.append(part)
                            bound_references.append({"tag": tag, "source": str(ref_path)})

                clean_prompt = compile_clean_omni_prompt(scene.omni_prose_prompt)
                contents.append(clean_prompt)
                kwargs: Dict[str, Any] = {
                    "model": self.config.video_model,
                    "input": contents if bound_references else clean_prompt,
                    "seed": seed,
                }
                if is_mode_b and effective_prev_id:
                    kwargs["previous_interaction_id"] = effective_prev_id

                interaction = client.interactions.create(**kwargs)
                interaction_id = getattr(interaction, "id", f"live-{scene.scene_index}")
                record: Dict[str, Any] = {
                    "scene_index": scene.scene_index,
                    "interaction_id": interaction_id,
                    "status": "submitted",
                    "model": self.config.video_model,
                    "mode": bible.storytelling_mode.value,
                    "seed": seed,
                    "selected_take_id": params["selected_take_id"],
                    "end_frame_path": params["end_frame_path"],
                    "clean_prose_prompt": clean_prompt,
                    "bound_references": bound_references[:3],
                }
                if is_mode_b:
                    record["previous_interaction_id"] = effective_prev_id
                results.append(record)
                prev_interaction_id = interaction_id
            except Exception as e:
                results.append({
                    "scene_index": scene.scene_index,
                    "status": "error",
                    "seed": seed,
                    "selected_take_id": params["selected_take_id"],
                    "end_frame_path": params["end_frame_path"],
                    "error_message": str(e),
                })

        return results
