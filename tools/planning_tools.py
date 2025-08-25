import os
import json
from datetime import datetime

PLANS_FILE = os.path.join(os.path.dirname(__file__), 'plans.json')

class PlanManager:
    def __init__(self, file_path=PLANS_FILE):
        self.file_path = file_path
        self.plans = self.load_plans()

    def load_plans(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    else:
                        return []
            except Exception:
                return []
        return []

    def save_plans(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.plans, f, ensure_ascii=False, indent=2)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_plans(self):
        return self.plans

    def add_plan(self, text, status="new"):
        try:
            new_id = str(len(self.plans) + 1)
            now = datetime.now()
            plan = {
                "id": new_id,
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M'),
                "text": text,
                "status": status  # 'new' or 'done'
            }
            self.plans.append(plan)
            save_result = self.save_plans()
            if save_result["status"] == "success":
                return {"status": "success", "id": new_id, "plan": plan}
            else:
                return {"status": "error", "message": save_result.get("message", "Failed to save plan.")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_plan(self, plan_id, new_text=None, new_status=None):
        for plan in self.plans:
            if plan['id'] == plan_id:
                updated = False
                if new_text is not None:
                    plan['text'] = new_text
                    updated = True
                if new_status is not None:
                    # Accept boolean or string; normalize boolean to 'done'/'new'
                    if isinstance(new_status, bool):
                        plan['status'] = 'done' if new_status else 'new'
                    else:
                        plan['status'] = new_status
                    updated = True
                if not updated:
                    return {"status": "error", "id": plan_id, "message": "No updates provided."}
                save_result = self.save_plans()
                if save_result["status"] == "success":
                    return {"status": "success", "id": plan_id, "plan": plan}
                else:
                    return {"status": "error", "id": plan_id, "message": save_result.get("message", "Failed to save plan.")}
        return {"status": "error", "id": plan_id, "message": "Plan id not found."}

    def delete_plans(self, ids):
        found = set()
        for id_ in ids:
            if any(p['id'] == id_ for p in self.plans):
                found.add(id_)
        self.plans = [p for p in self.plans if p['id'] not in found]
        # Renumber IDs after deletion
        for idx, plan in enumerate(self.plans, start=1):
            plan['id'] = str(idx)
        save_result = self.save_plans()
        results = []
        for id_ in ids:
            if id_ in found:
                if save_result["status"] == "success":
                    results.append({"status": "success", "id": id_})
                else:
                    results.append({"status": "error", "id": id_, "message": save_result.get("message", "Failed to save plans.")})
            else:
                results.append({"status": "error", "id": id_, "message": "Plan id not found."})
        return results


class GetPlansTool:
    schema = {
        "type": "function",
        "name": "get_plans",
        "description": (
            "Retrieve the current ordered plan steps (id, date, time, text, status). Always call before: (a) creating a new plan phase, (b) executing a step if state may have changed, (c) revising or deleting steps. "
            "Use to synchronize internal reasoning with persisted plan state so you never act on stale assumptions."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    }

    def run(self, **kwargs):
        plan_manager = PlanManager()
        return {"status": "success", "plans": plan_manager.get_plans()}


class CreatePlanTool:
    schema = {
        "type": "function",
        "name": "create_plan",
        "description": (
            "Materialize a new phase or initial set of atomic steps for solving a complex problem. Provide an ordered list of step texts (each one executable without further decomposition). "
            "Call only after inspecting existing steps with get_plans and only for steps not already present. Newly created steps start with status='new'."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string", "description": "Each text is one plan step."},
                    "description": "A list of plan step texts to save. Each text is one plan step.",
                }
            },
            "required": ["texts"],
            "additionalProperties": False,
        },
    }

    def run(self, texts):
        plan_manager = PlanManager()
        results = []
        for text in texts:
            result = plan_manager.add_plan(text)
            results.append(result)
        return results


class UpdatePlanTool:
    schema = {
        "type": "function",
        "name": "update_plan",
        "description": (
            "Revise existing plan steps or mark them complete. Typical usage: after executing a step, set status='done'. You may also refine the wording of future steps to reflect new context. "
            "Provide a list of entries each with an 'id' plus optional 'text' and/or 'status'. If a provider requires sending all fields, resend unchanged text/status values."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "The id of the plan to update."},
                            "text": {"type": "string", "description": "(Optional) The new text for the plan step."},
                            "status": {"type": "string", "enum": ["new", "done"], "description": "(Optional) 'new' = not executed; 'done' = executed."},
                        },
                        # Keep only 'id' formally required so callers can send minimal diffs if the runtime / model allows.
                        "required": ["id", "text", "status"],
                        "additionalProperties": False,
                    },
                    "description": "A list of plan updates, each with id and optional new text/status.",
                }
            },
            "required": ["entries"],
            "additionalProperties": False,
        },
    }

    def run(self, entries):
        plan_manager = PlanManager()
        results = []
        for entry in entries:
            result = plan_manager.update_plan(entry["id"], entry.get("text"), entry.get("status"))
            results.append(result)
        return results


class DeletePlanTool:
    schema = {
        "type": "function",
        "name": "delete_plan",
        "description": (
            "Remove obsolete or superseded plan steps by id. Use this when re-planning causes certain steps to become irrelevant, or after splitting/merging steps. Remaining steps are re-numbered consecutively starting at 1—always re-fetch with get_plans after deletion before further updates."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string", "description": "The id of the plan to delete."},
                    "description": "A list of plan ids to delete.",
                }
            },
            "required": ["ids"],
            "additionalProperties": False,
        },
    }

    def run(self, ids):
        plan_manager = PlanManager()
        results = plan_manager.delete_plans(ids)
        return results
