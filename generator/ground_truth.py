import pandas as pd

from .config import (
    PATHS,
    RING_ACCOUNT_START,
    RING_ACCOUNT_END,
)

# ============================================================
# GENERATE GROUND TRUTH
# ============================================================


def generate_ground_truth(
    accounts,
    ring_members,
):

    ground_truth = accounts[["account_id"]].copy()

    # Default: not a true ring member.
    ground_truth["abuse_ring_id"] = None

    ground_truth["true_ring_member"] = False

    ground_truth["ring_type"] = None

    ground_truth["ring_start_time"] = pd.NaT

    ground_truth["ring_end_time"] = pd.NaT

    # Apply actual ring membership.
    for member in ring_members:

        mask = ground_truth["account_id"] == member["account_id"]

        ground_truth.loc[
            mask,
            "abuse_ring_id",
        ] = member["abuse_ring_id"]

        ground_truth.loc[
            mask,
            "true_ring_member",
        ] = True

        ground_truth.loc[
            mask,
            "ring_type",
        ] = member["ring_type"]

        ground_truth.loc[
            mask,
            "ring_start_time",
        ] = member["ring_start_time"]

        ground_truth.loc[
            mask,
            "ring_end_time",
        ] = member["ring_end_time"]

    return ground_truth


# ============================================================
# SAVE
# ============================================================


def run_ground_truth(
    accounts,
    ring_members,
):

    ground_truth = generate_ground_truth(
        accounts,
        ring_members,
    )

    ground_truth.to_csv(
        PATHS["ring_ground_truth"],
        index=False,
    )

    print(f"Ground-truth accounts: " f"{len(ground_truth):,}")

    print("True ring members: " f"{ground_truth['true_ring_member'].sum():,}")

    print("\nRing distribution:")

    print(ground_truth[ground_truth["true_ring_member"]]["ring_type"].value_counts())

    return ground_truth


if __name__ == "__main__":

    accounts = pd.read_csv(PATHS["accounts"])

    # Standalone execution isn't intended
    # to reconstruct ring_members.
    print("Run ground_truth through " "generate_dataset.py")
