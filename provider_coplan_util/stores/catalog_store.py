"""套餐与模型目录持久化（qwenplan 兼容语义）。"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = ["CatalogStore"]


def _normalize_features(features: Any) -> List[str]:
    if isinstance(features, list):
        return [str(item) for item in features]
    if isinstance(features, str):
        text = features.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except Exception:
            pass
        return [line for line in text.split("\n") if line.strip()]
    return []


def _normalize_selected_models(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except Exception:
            pass
    return []


class CatalogStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._plans_path = self._dir / "plans.json"
        self._models_path = self._dir / "models.json"

    def ensure_defaults(
        self,
        default_plans: List[Dict[str, Any]],
        default_models: List[Dict[str, Any]],
    ) -> None:
        if not self._plans_path.is_file():
            seeded: List[Dict[str, Any]] = []
            for plan in default_plans:
                seeded.append({
                    "id": str(plan.get("id") or uuid.uuid4()),
                    "name": plan.get("name") or "",
                    "price": int(plan.get("price") or 0),
                    "requests_per_5h": int(plan.get("requests_per_5h") or 0),
                    "requests_per_month": int(plan.get("requests_per_month") or 0),
                    "description": plan.get("description") or "",
                    "features": _normalize_features(plan.get("features")),
                    "selected_models": _normalize_selected_models(plan.get("selected_models")),
                    "strategy_id": str(plan.get("strategy_id") or ""),
                    "entry_alias": str(plan.get("entry_alias") or ""),
                    "is_active": bool(plan.get("is_active", True)),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                })
            self._save_plans(seeded)
        if not self._models_path.is_file():
            seeded_models: List[Dict[str, Any]] = []
            for index, model in enumerate(default_models):
                seeded_models.append({
                    "id": index + 1,
                    "model_id": str(model.get("model_id") or ""),
                    "display_name": str(model.get("display_name") or ""),
                    "description": str(model.get("description") or ""),
                    "sort_order": int(model.get("sort_order") or index),
                    "is_active": bool(model.get("is_active", True)),
                    "created_at": int(time.time()),
                })
            self._save_models(seeded_models)

    def _load_plans(self) -> List[Dict[str, Any]]:
        if not self._plans_path.is_file():
            return []
        data = json.loads(self._plans_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _save_plans(self, plans: List[Dict[str, Any]]) -> None:
        self._plans_path.write_text(
            json.dumps(plans, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_models(self) -> List[Dict[str, Any]]:
        if not self._models_path.is_file():
            return []
        data = json.loads(self._models_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _save_models(self, models: List[Dict[str, Any]]) -> None:
        self._models_path.write_text(
            json.dumps(models, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _public_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        features = _normalize_features(plan.get("features"))
        selected = _normalize_selected_models(plan.get("selected_models"))
        return {
            **plan,
            "features": json.dumps(features, ensure_ascii=False),
            "selected_models": json.dumps(selected, ensure_ascii=False),
        }

    def list_plans(self, *, active_only: bool = False) -> List[Dict[str, Any]]:
        plans = sorted(self._load_plans(), key=lambda item: (item.get("price", 0), item.get("name", "")))
        if active_only:
            plans = [plan for plan in plans if plan.get("is_active", True)]
        return [self._public_plan(plan) for plan in plans]

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        for plan in self._load_plans():
            if str(plan.get("id")) == str(plan_id):
                return self._public_plan(plan)
        return None

    def create_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("name required")
        plans = self._load_plans()
        entry = {
            "id": str(uuid.uuid4()),
            "name": name,
            "price": int(data.get("price") or 0),
            "requests_per_5h": int(data.get("requests_per_5h") or 0),
            "requests_per_month": int(data.get("requests_per_month") or 0),
            "description": str(data.get("description") or ""),
            "features": _normalize_features(data.get("features")),
            "selected_models": _normalize_selected_models(data.get("selected_models")),
            "strategy_id": str(data.get("strategy_id") or ""),
            "entry_alias": str(data.get("entry_alias") or ""),
            "is_active": bool(data.get("is_active", True)),
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        plans.append(entry)
        self._save_plans(plans)
        return self._public_plan(entry)

    def update_plan(self, plan_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        plans = self._load_plans()
        for plan in plans:
            if str(plan.get("id")) != str(plan_id):
                continue
            if "name" in data:
                name = str(data.get("name") or "").strip()
                if not name:
                    raise ValueError("name required")
                plan["name"] = name
            if "price" in data:
                plan["price"] = int(data.get("price") or 0)
            if "requests_per_5h" in data:
                plan["requests_per_5h"] = int(data.get("requests_per_5h") or 0)
            if "requests_per_month" in data:
                plan["requests_per_month"] = int(data.get("requests_per_month") or 0)
            if "description" in data:
                plan["description"] = str(data.get("description") or "")
            if "features" in data:
                plan["features"] = _normalize_features(data.get("features"))
            if "selected_models" in data:
                plan["selected_models"] = _normalize_selected_models(data.get("selected_models"))
            if "strategy_id" in data:
                plan["strategy_id"] = str(data.get("strategy_id") or "")
            if "entry_alias" in data:
                plan["entry_alias"] = str(data.get("entry_alias") or "")
            if "is_active" in data:
                plan["is_active"] = bool(data.get("is_active"))
            plan["updated_at"] = int(time.time())
            self._save_plans(plans)
            return self._public_plan(plan)
        raise KeyError(plan_id)

    def delete_plan(self, plan_id: str) -> bool:
        plans = self._load_plans()
        new_plans = [plan for plan in plans if str(plan.get("id")) != str(plan_id)]
        if len(new_plans) == len(plans):
            return False
        self._save_plans(new_plans)
        return True

    def list_models(self) -> List[Dict[str, Any]]:
        return sorted(self._load_models(), key=lambda item: (item.get("sort_order", 0), item.get("model_id", "")))

    def add_model(self, data: Dict[str, Any]) -> Dict[str, Any]:
        model_id = str(data.get("model_id") or "").strip()
        display_name = str(data.get("display_name") or "").strip()
        if not model_id or not display_name:
            raise ValueError("model_id and display_name required")
        models = self._load_models()
        for model in models:
            if model.get("model_id") == model_id:
                model["display_name"] = display_name
                model["description"] = str(data.get("description") or "")
                model["sort_order"] = int(data.get("sort_order") or model.get("sort_order") or 0)
                model["is_active"] = True
                self._save_models(models)
                return model
        next_id = max((int(model.get("id") or 0) for model in models), default=0) + 1
        entry = {
            "id": next_id,
            "model_id": model_id,
            "display_name": display_name,
            "description": str(data.get("description") or ""),
            "sort_order": int(data.get("sort_order") or 0),
            "is_active": True,
            "created_at": int(time.time()),
        }
        models.append(entry)
        self._save_models(models)
        return entry

    def toggle_model(self, model_id: str, is_active: bool) -> bool:
        models = self._load_models()
        changed = False
        for model in models:
            if model.get("model_id") == model_id:
                model["is_active"] = bool(is_active)
                changed = True
                break
        if changed:
            self._save_models(models)
        return changed

    def delete_model(self, model_id: str) -> bool:
        models = self._load_models()
        new_models = [model for model in models if model.get("model_id") != model_id]
        if len(new_models) == len(models):
            return False
        self._save_models(new_models)
        return True
