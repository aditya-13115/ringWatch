import pandas as pd
from .features_config import (
    GROUND_TRUTH_PATH,
    PREDICTIONS_TEST_PATH,
    PATHS,
    MODEL_A_PATH,
    MODEL_B_PATH,
)
from .config import PATHS as RAW_PATHS


def hard_negative_fp_breakdown(predictions_path=PREDICTIONS_TEST_PATH):
    preds = pd.read_csv(predictions_path)
    gt = pd.read_csv(GROUND_TRUTH_PATH)
    private = pd.read_csv(
        RAW_PATHS["accounts"].parent / "account_population_labels_private.csv"
    )
    # Merge preds with gt and private
    df = preds.merge(
        gt[["account_id", "true_ring_member", "abuse_ring_id"]],
        on="account_id",
        how="left",
    )
    df = df.merge(
        private[["account_id", "population_type"]], on="account_id", how="left"
    )
    # For test set, identify false positives that are hard negatives
    # Assuming preds has proba_B and pred_B columns, and we want Model B predictions.
    hard_fps = df[
        (df["pred_B"] == 1)
        & (df["true_ring_member"] == False)
        & (df["population_type"] == "hard_negative")
    ]
    # Analyze distribution of hard-negative archetypes? We don't have archetype labels, but we can look at features.
    # Instead, we can merge with features to see their characteristics.
    features = pd.read_csv(
        RAW_PATHS["accounts"].parent / "processed" / "features_graph.csv"
    )
    hard_fps_features = hard_fps.merge(features, on="account_id", how="left")
    print("Hard-negative false positives (Model B):", len(hard_fps))
    print(
        hard_fps_features[
            [
                "account_id",
                "return_rate",
                "coupon_usage_rate",
                "shared_device_count",
                "shared_address_count",
            ]
        ].describe()
    )


if __name__ == "__main__":
    hard_negative_fp_breakdown()
