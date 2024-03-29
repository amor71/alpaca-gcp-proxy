import pandas as pd
from google.cloud import exceptions, firestore  # type: ignore

from ..logger import log_error


class Mission:
    # TODO: move to database
    level_step: dict = {
        0: 0,
        200: 25,
        1000: 50,
        2500: 100,
        5000: 250,
        15000: 500,
        20000: 750,
        40000: 1000,
        150000: 2000,
    }

    def __init__(self, data: dict):
        self.data = data

    def forecaster(self, bins: int = 30) -> list:
        initial_investment = int(self.data.get("initial_amount") or 0)
        weekly_topup = int(self.data.get("weekly_topup") or 0)

        print(
            f"initial_investment={initial_investment} weekly_topup={weekly_topup}"
        )

        if not initial_investment and not weekly_topup:
            log_error(
                "forecaster()",
                "can not create forecast when without both initial investment and weekly topup",
            )
            return []

        num_years_to_calc = 30
        annual_interest = 0.1
        weekly_interest = annual_interest / 52
        num_weeks = 52 * num_years_to_calc

        deposit = [weekly_topup] * num_weeks
        deposit[0] += initial_investment
        rate = [weekly_interest] * num_weeks

        df = pd.DataFrame({"deposit": deposit, "rate": rate})
        df["total"] = (
            df["deposit"] * df["rate"].shift().add(1).cumprod().fillna(1)
        ).cumsum()
        df["year"] = df.index // (52 * num_years_to_calc / bins)

        new_df = pd.DataFrame(
            {
                "deposit": df.groupby("year").sum()["deposit"].cumsum(),
                "amount": df.groupby("year").last()["total"],
            }
        ).round(1)

        return new_df.values.tolist()

    def calculate_milestones(self, account_size: int) -> list[int]:
        keys = list(self.level_step.keys())
        index = min(
            range(len(keys)), key=lambda i: abs(keys[i] - account_size)
        )
        level = keys[index + 1]

        past_milestone = (
            account_size // self.level_step[level]
        ) * self.level_step[level]

        next_milestones = [
            past_milestone + (i + 1) * self.level_step[level] for i in range(3)
        ]

        return [past_milestone, *next_milestones]


class Missions:
    def __init__(self, user_id: str | None = None) -> None:
        self.user_id = user_id
        self.missions = self._load_missions() if user_id else None

    @property
    def exists(self) -> bool:
        """Return True if User object is populated with data"""

        return self.missions != None

    def __iter__(self):
        if not self.exists:
            return None

        yield from self.missions

    def _load_missions(self):
        db = firestore.Client()

        docs = (
            db.collection("missions")
            .document(self.user_id)
            .collection("user_missions")
            .stream()
        )

        return [Mission(doc_ref.to_dict()) for doc_ref in docs]

    @classmethod
    def exists_by_name(cls, user_id: str, mission_name: str) -> bool:
        db = firestore.Client()

        ref = (
            db.collection("missions")
            .document(user_id)
            .collection("user_missions")
        )

        docs = ref.where(
            filter=firestore.FieldFilter("name", "==", mission_name)
        ).stream()

        return len(list(docs)) > 0

    @classmethod
    def add(
        cls,
        user_id: str,
        mission_name: str,
        strategy: str,
        initial_amount: str | None,
        weekly_topup: str | None,
    ) -> str:
        data = {
            "name": mission_name,
            "strategy": strategy,
            "created": firestore.SERVER_TIMESTAMP,
        }

        if initial_amount:
            data["initial_amount"] = initial_amount
        if weekly_topup:
            data["weekly_topup"] = weekly_topup

        db = firestore.Client()
        doc_ref = (
            db.collection("missions")
            .document(user_id)
            .collection("user_missions")
            .document()
        )

        _ = doc_ref.set(data)

        return doc_ref.id


class Runs:
    def __init__(self, data: dict):
        self.data = data

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def strategy(self) -> str:
        return self.data["strategy"]

    @classmethod
    def add(
        cls, user_id: str, run_id: str, mission_name: str, strategy: str
    ) -> str:
        data = {
            "name": mission_name,
            "strategy": strategy,
            "created": firestore.SERVER_TIMESTAMP,
        }

        db = firestore.Client()

        _ = (
            db.collection("runs")
            .document(user_id)
            .collection("list")
            .document(run_id)
            .set(document_data=data, merge=True)
        )

        return run_id

    @classmethod
    def update(cls, user_id: str, run_id: str, details: dict) -> None:
        db = firestore.Client()

        _ = (
            db.collection("runs")
            .document(user_id)
            .collection("list")
            .document(run_id)
            .set(document_data=details, merge=True)
        )

    @classmethod
    def load(cls, user_id: str, run_id: str):
        db = firestore.Client()
        doc = (
            db.collection("runs")
            .document(user_id)
            .collection("list")
            .document(run_id)
            .get()
        )

        if doc.exists:
            return Runs(doc.to_dict())

        log_error("reschedule_run_by_run_id", "could not load run {run_id}")
        return None
