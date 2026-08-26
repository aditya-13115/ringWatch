import json
from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd

from .config import SEED
from .features_config import (
    PREDICTION_CUTOFF,
    FEATURES_PATH,
    GRAPH_EDGES_PATH,
    COMMUNITIES_PATH,
    FEATURES_GRAPH_PATH,
    BASELINE_METRICS_PATH,
    DAY5_LEAKAGE_REPORT_PATH,
    GROUND_TRUTH_PATH,
    PATHS,
)

# ============================================================
# CONSTANTS
# ============================================================

T = pd.Timestamp(PREDICTION_CUTOFF)



FORBIDDEN_COLUMNS = [
    "population_type",
    "abuse_ring_id",
    "true_ring_member",
    "ring_type",
    "ring_start_time",
    "ring_end_time",
]

ALLOWED_EDGE_WEIGHTS = {
    1.0,
    0.7,
    0.3,
    0.2,
}

STRONG_EDGE_RULES = [
    ("device_id", "shares_device", 1.0),
    ("instrument_id", "shares_payment_instrument", 1.0),
    ("phone_hash", "shares_phone", 1.0),
    ("address_id", "shares_address", 0.7),
]


# ============================================================
# LOAD DATA
# ============================================================


def load_day5_data():
    """
    Load only the datasets required for Day 5 graph construction.

    Ground truth is deliberately NOT loaded here.

    Datetime columns are explicitly normalized after CSV loading
    because some source CSVs contain mixed-type values.
    """

    features = pd.read_csv(
        FEATURES_PATH,
        low_memory=False,
    )

    accounts = pd.read_csv(
        PATHS["accounts"],
        low_memory=False,
    )

    orders = pd.read_csv(
        PATHS["orders"],
        low_memory=False,
    )

    devices = pd.read_csv(
        PATHS["devices"],
        low_memory=False,
    )

    addresses = pd.read_csv(
        PATHS["addresses"],
        low_memory=False,
    )

    phones = pd.read_csv(
        PATHS["phones"],
        low_memory=False,
    )

    instruments = pd.read_csv(
        PATHS["payment_instruments"],
        low_memory=False,
    )

    # ========================================================
    # EXPLICIT DATETIME NORMALIZATION
    # ========================================================

    datetime_columns = {
        "accounts": [
            "account_created_at",
        ],
        "orders": [
            "order_timestamp",
            "delivery_timestamp",
            "return_timestamp",
            "refund_timestamp",
            "dispute_created_at",
        ],
        "devices": [
            "first_seen_at",
        ],
        "addresses": [
            "first_seen_at",
        ],
        "phones": [
            "first_seen_at",
        ],
        "instruments": [
            "first_seen_at",
        ],
    }

    dataframes = {
        "accounts": accounts,
        "orders": orders,
        "devices": devices,
        "addresses": addresses,
        "phones": phones,
        "instruments": instruments,
    }

    for name, columns in datetime_columns.items():
        df = dataframes[name]

        for column in columns:
            if column in df.columns:
                df[column] = pd.to_datetime(
                    df[column],
                    errors="coerce",
                )

        dataframes[name] = df

    accounts = dataframes["accounts"]
    orders = dataframes["orders"]
    devices = dataframes["devices"]
    addresses = dataframes["addresses"]
    phones = dataframes["phones"]
    instruments = dataframes["instruments"]

    return (
        features,
        accounts,
        orders,
        devices,
        addresses,
        phones,
        instruments,
    )


# ============================================================
# VALIDATE DAY 4 FEATURES
# ============================================================


def validate_day4_features(features):
    """
    Validate the Day 4 feature matrix before using it.
    """

    assert features["account_id"].nunique() == len(features), (
        "Day 4 feature matrix must contain exactly one row per account."
    )

    assert features[
        "account_id"
    ].is_unique, "features_accounts.csv must contain exactly one row per account."

    assert (
        features["account_id"].notna().all()
    ), "features_accounts.csv contains missing account IDs."

    missing = int(features.isna().sum().sum())

    assert missing == 0, f"features_accounts.csv contains {missing} missing values."

    present_forbidden = [
        column for column in FORBIDDEN_COLUMNS if column in features.columns
    ]

    assert not present_forbidden, (
        f"Forbidden columns found in Day 4 features: " f"{present_forbidden}"
    )


# ============================================================
# FILTER TO CUTOFF
# ============================================================


def filter_to_cutoff(
    orders,
    devices,
    addresses,
    phones,
    instruments,
):
    """
    Apply exactly the same cutoff semantics as Day 4.

    Orders are retained based on order_timestamp.
    Entity tables are retained based on first_seen_at.
    """
    # --------------------------------------------------------
    # Datetime validation
    # --------------------------------------------------------

    required_datetime_columns = {
        "orders": ["order_timestamp"],
        "devices": ["first_seen_at"],
        "addresses": ["first_seen_at"],
        "phones": ["first_seen_at"],
        "instruments": ["first_seen_at"],
    }

    dataframes = {
        "orders": orders,
        "devices": devices,
        "addresses": addresses,
        "phones": phones,
        "instruments": instruments,
    }

    for name, columns in required_datetime_columns.items():
        df = dataframes[name]

        for column in columns:
            if column not in df.columns:
                raise KeyError(
                    f"{name} is missing required datetime column: {column}"
                )

            if not pd.api.types.is_datetime64_any_dtype(df[column]):
                raise TypeError(
                    f"{name}[{column}] is not datetime dtype: "
                    f"{df[column].dtype}"
                )

    filtered_orders = orders[orders["order_timestamp"] <= T].copy()

    filtered_devices = devices[devices["first_seen_at"] <= T].copy()

    filtered_addresses = addresses[addresses["first_seen_at"] <= T].copy()

    filtered_phones = phones[phones["first_seen_at"] <= T].copy()

    filtered_instruments = instruments[instruments["first_seen_at"] <= T].copy()

    # --------------------------------------------------------
    # Cutoff assertions
    # --------------------------------------------------------

    if len(filtered_orders) > 0:
        assert filtered_orders["order_timestamp"].max() <= T

    if len(filtered_devices) > 0:
        assert filtered_devices["first_seen_at"].max() <= T

    if len(filtered_addresses) > 0:
        assert filtered_addresses["first_seen_at"].max() <= T

    if len(filtered_phones) > 0:
        assert filtered_phones["first_seen_at"].max() <= T

    if len(filtered_instruments) > 0:
        assert filtered_instruments["first_seen_at"].max() <= T

    return (
        filtered_orders,
        filtered_devices,
        filtered_addresses,
        filtered_phones,
        filtered_instruments,
    )


# ============================================================
# EDGE STORAGE
# ============================================================


def normalize_pair(account_a, account_b):
    """
    Return a deterministic unordered account pair.
    """

    if account_a == account_b:
        return None

    return tuple(sorted((account_a, account_b)))


def add_edge_candidate(
    edge_map,
    account_a,
    account_b,
    edge_type,
    weight,
):
    """
    Add an edge candidate while retaining all evidence internally.

    edge_map:
        pair -> {
            "max_weight": float,
            "strongest_edge_type": str,
            "edge_types": set[str],
        }
    """

    pair = normalize_pair(account_a, account_b)

    if pair is None:
        return

    if weight not in ALLOWED_EDGE_WEIGHTS:
        raise ValueError(f"Invalid edge weight: {weight}")

    if pair not in edge_map:
        edge_map[pair] = {
            "max_weight": weight,
            "strongest_edge_type": edge_type,
            "edge_types": {edge_type},
        }
        return

    record = edge_map[pair]

    record["edge_types"].add(edge_type)

    # Keep maximum weight.
    if weight > record["max_weight"]:
        record["max_weight"] = weight
        record["strongest_edge_type"] = edge_type

    # Deterministic tie-break.
    elif weight == record["max_weight"]:
        if edge_type < record["strongest_edge_type"]:
            record["strongest_edge_type"] = edge_type


# ============================================================
# STRONG IDENTITY EDGES
# ============================================================


def build_strong_edges(filtered_orders, edge_map):
    """
    Build edges from shared device, payment instrument,
    phone, and address.
    """

    edge_counts = {
        "shares_device": 0,
        "shares_payment_instrument": 0,
        "shares_phone": 0,
        "shares_address": 0,
    }

    for entity_column, edge_type, weight in STRONG_EDGE_RULES:

        if entity_column not in filtered_orders.columns:
            raise KeyError(f"Missing required order column: {entity_column}")

        grouped = (
            filtered_orders[["account_id", entity_column]]
            .dropna(subset=[entity_column])
            .groupby(entity_column)["account_id"]
            .apply(set)
        )

        for entity, accounts in grouped.items():

            if pd.isna(entity):
                continue

            account_list = sorted(accounts)

            for account_a, account_b in combinations(
                account_list,
                2,
            ):
                add_edge_candidate(
                    edge_map,
                    account_a,
                    account_b,
                    edge_type,
                    weight,
                )

                edge_counts[edge_type] += 1

    return edge_counts


# ============================================================
# IP PREFIX EDGES
# ============================================================


def has_order_pair_within_24h(times_a, times_b):
    """
    Return True if any cross-account order pair is <= 24 hours apart.

    Uses a two-pointer approach instead of checking every possible
    timestamp pair.
    """

    i = 0
    j = 0

    times_a = sorted(times_a)
    times_b = sorted(times_b)

    while i < len(times_a) and j < len(times_b):

        difference = abs(times_a[i] - times_b[j])

        if difference <= pd.Timedelta(hours=24):
            return True

        if times_a[i] < times_b[j]:
            i += 1
        else:
            j += 1

    return False


def build_ip_edges(
    filtered_orders,
    filtered_devices,
    edge_map,
):
    """
    Build shared_ip_prefix edges.

    Two accounts are connected only when:
    - they share an IP prefix, and
    - at least one pair of their orders occurred within 24 hours.
    """

    required_columns = {
        "device_id",
        "account_id",
        "order_timestamp",
    }

    missing = required_columns - set(filtered_orders.columns)

    if missing:
        raise KeyError(f"Orders missing required columns: {sorted(missing)}")

    if "ip_prefix" not in filtered_devices.columns:
        raise KeyError("devices.csv must contain ip_prefix for Day 5.")

    device_ip = filtered_devices[["device_id", "ip_prefix"]].drop_duplicates()

    orders_with_ip = filtered_orders.merge(
        device_ip,
        on="device_id",
        how="left",
    )

    edge_count = 0

    for ip_prefix, group in orders_with_ip.groupby(
        "ip_prefix",
        dropna=True,
    ):

        accounts_data = {}

        for account_id, account_orders in group.groupby("account_id"):
            timestamps = (
                account_orders["order_timestamp"].dropna().sort_values().tolist()
            )

            if timestamps:
                accounts_data[account_id] = timestamps

        account_ids = sorted(accounts_data)

        for account_a, account_b in combinations(
            account_ids,
            2,
        ):

            if has_order_pair_within_24h(
                accounts_data[account_a],
                accounts_data[account_b],
            ):
                add_edge_candidate(
                    edge_map,
                    account_a,
                    account_b,
                    "shares_ip_prefix",
                    0.3,
                )

                edge_count += 1

    return edge_count


# ============================================================
# RARE COUPON EDGES
# ============================================================


def build_coupon_edges(
    filtered_orders,
    edge_map,
):
    """
    Build weak edges for coupons used fewer than 10 times.

    Coupon frequency is calculated exclusively from pre-T orders.
    """

    if "coupon_code" not in filtered_orders.columns:
        raise KeyError("orders.csv must contain coupon_code for Day 5.")

    orders_with_coupon = filtered_orders[
        filtered_orders["coupon_code"].notna()
        & (filtered_orders["coupon_code"].astype(str).str.strip() != "")
    ].copy()

    coupon_counts = orders_with_coupon["coupon_code"].value_counts()

    rare_coupons = coupon_counts[coupon_counts < 10].index

    edge_count = 0

    for coupon in rare_coupons:

        accounts = (
            orders_with_coupon.loc[
                orders_with_coupon["coupon_code"] == coupon,
                "account_id",
            ]
            .dropna()
            .unique()
        )

        accounts = sorted(accounts)

        for account_a, account_b in combinations(
            accounts,
            2,
        ):
            add_edge_candidate(
                edge_map,
                account_a,
                account_b,
                "shares_coupon",
                0.2,
            )

            edge_count += 1

    return edge_count, coupon_counts, rare_coupons


# ============================================================
# FINALIZE EDGE DATAFRAME
# ============================================================


def finalize_edges(edge_map):
    """
    Convert internal edge map into the required CSV structure.
    """

    records = []

    for (
        account_pair,
        record,
    ) in edge_map.items():

        account_a, account_b = account_pair

        records.append(
            {
                "account_id_1": account_a,
                "account_id_2": account_b,
                "edge_type": record["strongest_edge_type"],
                "weight": float(record["max_weight"]),
            }
        )

    edge_df = pd.DataFrame(
        records,
        columns=[
            "account_id_1",
            "account_id_2",
            "edge_type",
            "weight",
        ],
    )

    if len(edge_df) > 0:
        edge_df = edge_df.sort_values(
            [
                "account_id_1",
                "account_id_2",
            ]
        ).reset_index(drop=True)

    return edge_df


# ============================================================
# EDGE VALIDATION
# ============================================================


def validate_edges(edge_df):
    """
    Validate final deduplicated account graph edges.
    """

    if len(edge_df) == 0:
        raise AssertionError("No graph edges were generated.")

    self_loops = (edge_df["account_id_1"] == edge_df["account_id_2"]).sum()

    assert self_loops == 0, f"Found {self_loops} self-loops."

    unordered_pairs = edge_df.apply(
        lambda row: tuple(
            sorted(
                (
                    row["account_id_1"],
                    row["account_id_2"],
                )
            )
        ),
        axis=1,
    )

    duplicate_pairs = unordered_pairs.duplicated().sum()

    assert duplicate_pairs == 0, f"Found {duplicate_pairs} duplicate unordered pairs."

    invalid_weights = (~edge_df["weight"].isin(ALLOWED_EDGE_WEIGHTS)).sum()

    assert invalid_weights == 0, f"Found {invalid_weights} invalid edge weights."

    unique_accounts = set(edge_df["account_id_1"]) | set(edge_df["account_id_2"])

    assert len(unique_accounts) > 0

    print("\n-----------------------------------")
    print("EDGE VALIDATION")
    print("-----------------------------------")

    print(f"Total edges:             {len(edge_df):,}")
    print(f"Unique accounts in edges: " f"{len(unique_accounts):,}")
    print(f"Self-loops:              {self_loops}")
    print(f"Duplicate unordered pairs: " f"{duplicate_pairs}")

    print("\nEdge type counts:")

    edge_type_counts = edge_df["edge_type"].value_counts()

    for edge_type in [
        "shares_device",
        "shares_payment_instrument",
        "shares_phone",
        "shares_address",
        "shares_ip_prefix",
        "shares_coupon",
    ]:
        print(f"{edge_type:<28}" f"{int(edge_type_counts.get(edge_type, 0)):>6}")

    return unique_accounts


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================


def build_graph(
    account_ids,
    edge_df,
):
    """
    Build an undirected weighted graph.

    All accounts are added first so isolated accounts are retained.
    """

    graph = nx.Graph()

    graph.add_nodes_from(account_ids)

    for row in edge_df.itertuples(index=False):
        graph.add_edge(
            row.account_id_1,
            row.account_id_2,
            weight=float(row.weight),
            edge_type=row.edge_type,
        )

    return graph


# ============================================================
# GRAPH INTEGRITY
# ============================================================


def graph_integrity_report(graph):
    """
    Report structural graph properties.
    """

    nodes = graph.number_of_nodes()
    edges = graph.number_of_edges()

    self_loops = nx.number_of_selfloops(graph)

    isolated_nodes = list(nx.isolates(graph))

    components = list(nx.connected_components(graph))

    component_sizes = sorted(
        (len(component) for component in components),
        reverse=True,
    )

    largest_component = component_sizes[0] if component_sizes else 0

    print("\n-----------------------------------")
    print("GRAPH INTEGRITY")
    print("-----------------------------------")

    print(f"Nodes:                  {nodes:,}")
    print(f"Edges:                  {edges:,}")
    print(f"Self-loops:             {self_loops:,}")
    print(f"Isolated nodes:         " f"{len(isolated_nodes):,}")
    print(f"Connected components:   " f"{len(components):,}")
    print(f"Largest component:      " f"{largest_component:,}")

    assert nodes > 0
    assert self_loops == 0
    assert edges > 0

    if len(isolated_nodes) == nodes:
        raise AssertionError("Every account is isolated. Graph construction is broken.")

    if largest_component == nodes:
        print(
            "WARNING: graph is fully connected. "
            "Inspect graph density before proceeding."
        )

    if len(isolated_nodes) > nodes * 0.90:
        print("WARNING: over 90% of accounts are isolated. " "Inspect edge generation.")

    degrees = dict(graph.degree())

    max_degree = max(
        degrees.values(),
        default=0,
    )

    print(f"Maximum degree:        " f"{max_degree:,}")

    return {
        "nodes": nodes,
        "edges": edges,
        "self_loops": self_loops,
        "isolated_nodes": len(isolated_nodes),
        "connected_components": len(components),
        "largest_component": largest_component,
        "max_degree": max_degree,
    }


# ============================================================
# LOUVAIN
# ============================================================


def run_louvain(graph):
    """
    Deterministic Louvain community detection.
    """

    communities = nx.community.louvain_communities(
        graph,
        weight="weight",
        seed=SEED,
    )

    communities = sorted(
        communities,
        key=lambda members: (
            -len(members),
            min(members),
        ),
    )

    community_records = []

    for community_id, members in enumerate(communities):
        for account_id in members:
            community_records.append(
                {
                    "account_id": account_id,
                    "community_id": community_id,
                }
            )

    community_df = pd.DataFrame(community_records)

    community_df = community_df.sort_values("account_id").reset_index(drop=True)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    assert len(community_df) == graph.number_of_nodes()
    assert community_df["account_id"].is_unique
    assert community_df["community_id"].notna().all()

    community_sizes = community_df["community_id"].value_counts()

    number_of_communities = len(community_sizes)

    largest_community = int(community_sizes.max())

    singleton_communities = int((community_sizes == 1).sum())

    print("\n-----------------------------------")
    print("LOUVAIN COMMUNITIES")
    print("-----------------------------------")

    print(f"Number of communities: " f"{number_of_communities:,}")

    print(f"Largest community:    " f"{largest_community:,}")

    print(f"Singleton communities: " f"{singleton_communities:,}")

    if number_of_communities == 1:
        print("WARNING: Louvain produced one community.")

    if largest_community == graph.number_of_nodes():
        print("WARNING: largest community contains all accounts.")

    return (
        community_df,
        community_sizes,
    )


# ============================================================
# NODE GRAPH FEATURES
# ============================================================


def compute_node_graph_features(graph):
    """
    Compute account-level graph metrics.
    """

    degree_centrality = nx.degree_centrality(graph)

    try:
        eigenvector_centrality = nx.eigenvector_centrality(
            graph,
            max_iter=1000,
            weight="weight",
        )
    except nx.PowerIterationFailedConvergence as exc:
        raise RuntimeError(
            "Eigenvector centrality failed to converge " "within 1000 iterations."
        ) from exc

    clustering = nx.clustering(
        graph,
        weight="weight",
    )

    triangle_counts = nx.triangles(graph)

    component_sizes = {}

    for component in nx.connected_components(graph):
        size = len(component)

        for account_id in component:
            component_sizes[account_id] = size

    records = []

    for account_id in graph.nodes():

        shared_edge_count = graph.degree(account_id)

        shared_edge_weight_sum = sum(
            data.get("weight", 1.0)
            for _, _, data in graph.edges(
                account_id,
                data=True,
            )
        )

        records.append(
            {
                "account_id": account_id,
                "degree_centrality": float(degree_centrality[account_id]),
                "eigenvector_centrality": float(eigenvector_centrality[account_id]),
                "triangle_count": int(triangle_counts[account_id]),
                "clustering_coefficient": float(clustering[account_id]),
                "connected_component_size": int(component_sizes[account_id]),
                "shared_edge_count": int(shared_edge_count),
                "shared_edge_weight_sum": float(shared_edge_weight_sum),
            }
        )

    graph_features = pd.DataFrame(records)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    assert len(graph_features) == graph.number_of_nodes()
    assert graph_features["account_id"].is_unique

    numeric_columns = [
        "degree_centrality",
        "eigenvector_centrality",
        "triangle_count",
        "clustering_coefficient",
        "connected_component_size",
        "shared_edge_count",
        "shared_edge_weight_sum",
    ]

    assert graph_features[numeric_columns].isna().sum().sum() == 0

    assert (graph_features["degree_centrality"] >= 0).all()

    assert (graph_features["eigenvector_centrality"] >= 0).all()

    assert (graph_features["connected_component_size"] >= 1).all()

    return graph_features


# ============================================================
# COMMUNITY FEATURES
# ============================================================


def compute_community_features(
    features,
    community_df,
):
    """
    Compute community-level aggregates using Day 4 features.

    Ground truth is not involved.
    """

    required_columns = [
        "account_id",
        "return_rate",
        "refund_rate",
        "avg_order_value",
        "total_orders",
    ]

    missing = [column for column in required_columns if column not in features.columns]

    if missing:
        raise KeyError(f"Missing Day 4 feature columns: {missing}")

    community_members = community_df.merge(
        features[required_columns],
        on="account_id",
        how="left",
        validate="one_to_one",
    )

    if community_members[required_columns[1:]].isna().sum().sum() > 0:
        raise AssertionError(
            "Missing Day 4 values while building " "community aggregates."
        )

    aggregates = (
        community_members.groupby("community_id")
        .agg(
            community_size=(
                "account_id",
                "count",
            ),
            community_return_rate=(
                "return_rate",
                "mean",
            ),
            community_refund_rate=(
                "refund_rate",
                "mean",
            ),
            community_avg_order_value=(
                "avg_order_value",
                "mean",
            ),
            community_total_orders=(
                "total_orders",
                "sum",
            ),
        )
        .reset_index()
    )

    result = community_df.merge(
        aggregates,
        on="community_id",
        how="left",
        validate="many_to_one",
    )

    assert (result["community_size"] >= 1).all()

    assert (result["community_return_rate"].between(0, 1)).all()

    assert (result["community_refund_rate"].between(0, 1)).all()

    return result


# ============================================================
# MERGE FINAL GRAPH FEATURES
# ============================================================


def build_final_features(
    features,
    graph_features,
    community_features,
):
    """
    Merge graph and community features with Day 4 features.
    """

    graph_only = graph_features.merge(
        community_features,
        on="account_id",
        how="left",
        validate="one_to_one",
    )

    final_features = features.merge(
        graph_only,
        on="account_id",
        how="left",
        validate="one_to_one",
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    assert len(final_features) == len(features)
    assert final_features["account_id"].is_unique

    present_forbidden = [
        column for column in FORBIDDEN_COLUMNS if column in final_features.columns
    ]

    assert not present_forbidden, f"Forbidden columns present: " f"{present_forbidden}"

    missing_count = int(final_features.isna().sum().sum())

    assert missing_count == 0, (
        f"Final graph feature matrix has " f"{missing_count} missing values."
    )

    numeric_columns = final_features.select_dtypes(include=[np.number]).columns

    assert np.isfinite(
        final_features[numeric_columns].to_numpy()
    ).all(), "Final features contain infinite values."

    print("\n-----------------------------------")
    print("FINAL GRAPH FEATURE MATRIX")
    print("-----------------------------------")

    print(f"Rows:                    " f"{len(final_features):,}")

    print(f"Columns:                 " f"{len(final_features.columns):,}")

    print(f"Missing values:          " f"{missing_count}")

    print("Forbidden columns:       " "NONE")

    return final_features


# ============================================================
# BASELINE RULES
# ============================================================


def apply_locked_baseline_rules(
    features_graph,
):
    """
    Apply the locked Day 5 baseline rules.

    IMPORTANT:
    This function does not access ground truth.
    """

    required_columns = [
        "return_rate",
        "total_orders",
        "shared_device_count",
        "account_creation_burst_score",
        "coupon_usage_rate",
        "community_size",
        "community_return_rate",
        "dispute_rate",
    ]

    missing = [
        column for column in required_columns if column not in features_graph.columns
    ]

    if missing:
        raise KeyError(f"Missing baseline feature columns: {missing}")

    r1 = (features_graph["return_rate"] > 0.5) & (features_graph["total_orders"] >= 2)

    r2 = (features_graph["shared_device_count"] >= 1) & (
        features_graph["return_rate"] > 0.3
    )

    r3 = (features_graph["account_creation_burst_score"] >= 5) & (
        features_graph["coupon_usage_rate"] > 0.5
    )

    r4 = (features_graph["community_size"] >= 4) & (
        features_graph["community_return_rate"] > 0.4
    )

    r5 = features_graph["dispute_rate"] > 0.3

    predicted_positive = r1 | r2 | r3 | r4 | r5

    predictions = features_graph[["account_id"]].copy()

    predictions["R1"] = r1.astype(bool)
    predictions["R2"] = r2.astype(bool)
    predictions["R3"] = r3.astype(bool)
    predictions["R4"] = r4.astype(bool)
    predictions["R5"] = r5.astype(bool)

    predictions["predicted_positive"] = predicted_positive.astype(bool)

    return predictions


# ============================================================
# EVALUATION
# ============================================================


def evaluate_baseline(
    predictions,
):
    """
    Evaluate predictions against ground truth.

    Ground truth is loaded only here.
    """

    ground_truth = pd.read_csv(GROUND_TRUTH_PATH)

    required_gt_columns = {
        "account_id",
        "true_ring_member",
    }

    missing = required_gt_columns - set(ground_truth.columns)

    if missing:
        raise KeyError(f"Ground truth missing columns: {sorted(missing)}")

    assert ground_truth["account_id"].is_unique

    evaluation = predictions.merge(
        ground_truth[
            [
                "account_id",
                "true_ring_member",
            ]
        ],
        on="account_id",
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    assert (evaluation["_merge"] == "both").all()

    evaluation = evaluation.drop(columns=["_merge"])

    evaluation["true_ring_member"] = evaluation["true_ring_member"].astype(bool)

    predicted = evaluation["predicted_positive"]

    actual = evaluation["true_ring_member"]

    tp = int((predicted & actual).sum())

    fp = int((predicted & ~actual).sum())

    tn = int((~predicted & ~actual).sum())

    fn = int((~predicted & actual).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    total_flagged = int(predicted.sum())

    true_ring_members_caught = tp

    # --------------------------------------------------------
    # Hard-negative reporting
    #
    # population_type is used ONLY here for evaluation
    # reporting, never as a model feature.
    # --------------------------------------------------------

    accounts = pd.read_csv(PATHS["accounts"])

    required_account_columns = {
        "account_id",
        "population_type",
    }

    missing = required_account_columns - set(accounts.columns)

    if missing:
        raise KeyError(f"accounts.csv missing columns: {sorted(missing)}")

    hard_negative_ids = set(
        accounts.loc[
            accounts["population_type"] == "hard_negative",
            "account_id",
        ]
    )

    hard_negative_false_positives = int(
        evaluation.loc[
            evaluation["predicted_positive"]
            & evaluation["account_id"].isin(hard_negative_ids),
            "account_id",
        ].nunique()
    )

    metrics = {
        "cutoff": str(T),
        "rules": [
            "R1: return_rate > 0.5 AND total_orders >= 2",
            "R2: shared_device_count >= 1 AND return_rate > 0.3",
            "R3: account_creation_burst_score >= 5 AND coupon_usage_rate > 0.5",
            "R4: community_size >= 4 AND community_return_rate > 0.4",
            "R5: dispute_rate > 0.3",
        ],
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "total_flagged": total_flagged,
        "true_ring_members_caught": true_ring_members_caught,
        "hard_negative_false_positives": hard_negative_false_positives,
    }

    return (
        metrics,
        evaluation,
    )


# ============================================================
# BASELINE REPORT
# ============================================================


def print_baseline_results(
    metrics,
    predictions,
):
    """
    Print baseline metrics and rule firing counts.
    """

    print("\n-----------------------------------")
    print("RULE BASELINE")
    print("-----------------------------------")

    print(f"R1 flags:               " f"{int(predictions['R1'].sum()):,}")

    print(f"R2 flags:               " f"{int(predictions['R2'].sum()):,}")

    print(f"R3 flags:               " f"{int(predictions['R3'].sum()):,}")

    print(f"R4 flags:               " f"{int(predictions['R4'].sum()):,}")

    print(f"R5 flags:               " f"{int(predictions['R5'].sum()):,}")

    print(f"Total flagged:          " f"{metrics['total_flagged']:,}")

    print(f"True ring members caught:" f" {metrics['true_ring_members_caught']:,}")

    print(f"Hard-negative FPs:      " f"{metrics['hard_negative_false_positives']:,}")

    print()

    print(f"Precision:              " f"{metrics['precision']:.4f}")

    print(f"Recall:                 " f"{metrics['recall']:.4f}")

    print(f"F1:                     " f"{metrics['f1']:.4f}")

    print("\nConfusion matrix:")
    print("[[TN, FP],")
    print(f" [{metrics['TN']}, {metrics['FP']}],")
    print(f" [{metrics['FN']}, {metrics['TP']}]]")


# ============================================================
# SAVE METRICS
# ============================================================


def save_baseline_metrics(metrics):
    """
    Save baseline metrics as JSON.
    """

    with open(
        BASELINE_METRICS_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics,
            file,
            indent=2,
        )

    print(f"\nBaseline metrics saved to:\n" f"{BASELINE_METRICS_PATH}")


# ============================================================
# DAY 5 LEAKAGE REPORT
# ============================================================


def write_day5_leakage_report(
    filtered_orders,
    filtered_devices,
    filtered_addresses,
    filtered_phones,
    filtered_instruments,
    coupon_counts,
    graph,
    features_graph,
):
    """
    Write the Day 5 cutoff/leakage report.

    Ground truth and population_type are intentionally not
    available to this function.
    """

    def max_or_na(df, column):
        if len(df) == 0:
            return "N/A"

        return df[column].max()

    max_order_timestamp = max_or_na(
        filtered_orders,
        "order_timestamp",
    )

    max_device_timestamp = max_or_na(
        filtered_devices,
        "first_seen_at",
    )

    max_address_timestamp = max_or_na(
        filtered_addresses,
        "first_seen_at",
    )

    max_phone_timestamp = max_or_na(
        filtered_phones,
        "first_seen_at",
    )

    max_instrument_timestamp = max_or_na(
        filtered_instruments,
        "first_seen_at",
    )

    all_cutoff_safe = True

    for timestamp in [
        max_order_timestamp,
        max_device_timestamp,
        max_address_timestamp,
        max_phone_timestamp,
        max_instrument_timestamp,
    ]:
        if timestamp != "N/A":
            if timestamp > T:
                all_cutoff_safe = False

    forbidden_present = [
        column for column in FORBIDDEN_COLUMNS if column in features_graph.columns
    ]

    graph_cutoff_safe = (
        all_cutoff_safe
        and len(graph) == len(features_graph)
        and len(forbidden_present) == 0
    )

    report = f"""
RingWatch — Day 5 Graph Leakage Report
=======================================

Prediction cutoff:
{T}

Max order timestamp used:
{max_order_timestamp}

Max device first_seen_at used:
{max_device_timestamp}

Max address first_seen_at used:
{max_address_timestamp}

Max phone first_seen_at used:
{max_phone_timestamp}

Max instrument first_seen_at used:
{max_instrument_timestamp}

IP relationships use order time:
YES — filtered order_timestamp <= T

Coupon rarity uses pre-T orders:
YES

Coupon observations used:
{len(coupon_counts):,}

Ground truth used for graph:
NO

Ground truth used for features:
NO

population_type used for features:
NO

Forbidden columns present in final features:
{forbidden_present if forbidden_present else "NONE"}

Louvain graph cutoff-safe:
{"YES" if graph_cutoff_safe else "NO"}

Graph nodes:
{graph.number_of_nodes():,}

Graph edges:
{graph.number_of_edges():,}

LEAKAGE CHECK:
{"PASSED" if graph_cutoff_safe else "FAILED"}
""".strip()

    with open(
        DAY5_LEAKAGE_REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(report + "\n")

    print(f"\nDay 5 leakage report saved to:\n" f"{DAY5_LEAKAGE_REPORT_PATH}")

    if not graph_cutoff_safe:
        raise AssertionError("Day 5 leakage check FAILED.")


# ============================================================
# MAIN
# ============================================================


def main():

    print("\n===================================")
    print("RINGWATCH DAY 5")
    print("CUTOFF-AWARE ACCOUNT GRAPH")
    print("===================================")

    # --------------------------------------------------------
    # 1. Load
    # --------------------------------------------------------

    (
        features,
        accounts,
        orders,
        devices,
        addresses,
        phones,
        instruments,
    ) = load_day5_data()

    validate_day4_features(features)

    assert len(accounts) == len(features), (
        f"Account table has {len(accounts):,} rows but Day 4 features have "
        f"{len(features):,} rows."
    )
    assert accounts["account_id"].is_unique

    # --------------------------------------------------------
    # 2. Cutoff filtering
    # --------------------------------------------------------

    print("\nFiltering data to prediction cutoff...")

    (
        filtered_orders,
        filtered_devices,
        filtered_addresses,
        filtered_phones,
        filtered_instruments,
    ) = filter_to_cutoff(
        orders,
        devices,
        addresses,
        phones,
        instruments,
    )

    print(f"Filtered orders:       " f"{len(filtered_orders):,}")

    print(f"Filtered devices:      " f"{len(filtered_devices):,}")

    print(f"Filtered addresses:    " f"{len(filtered_addresses):,}")

    print(f"Filtered phones:       " f"{len(filtered_phones):,}")

    print(f"Filtered instruments:  " f"{len(filtered_instruments):,}")

    # --------------------------------------------------------
    # 3–5. Build edges
    # --------------------------------------------------------

    print("\nBuilding account graph edges...")

    edge_map = {}

    strong_counts = build_strong_edges(
        filtered_orders,
        edge_map,
    )

    ip_edge_count = build_ip_edges(
        filtered_orders,
        filtered_devices,
        edge_map,
    )

    (
        coupon_edge_count,
        coupon_counts,
        rare_coupons,
    ) = build_coupon_edges(
        filtered_orders,
        edge_map,
    )

    edge_df = finalize_edges(edge_map)

    # --------------------------------------------------------
    # 6. Validate and save edges
    # --------------------------------------------------------

    validate_edges(edge_df)

    edge_df.to_csv(
        GRAPH_EDGES_PATH,
        index=False,
    )

    print(f"\nGraph edges saved to:\n" f"{GRAPH_EDGES_PATH}")

    # --------------------------------------------------------
    # Edge construction summary
    # --------------------------------------------------------

    print("\nRaw edge candidate counts:")
    print(f"shares_device:             " f"{strong_counts['shares_device']:,}")
    print(
        f"shares_payment_instrument: " f"{strong_counts['shares_payment_instrument']:,}"
    )
    print(f"shares_phone:              " f"{strong_counts['shares_phone']:,}")
    print(f"shares_address:            " f"{strong_counts['shares_address']:,}")
    print(f"shares_ip_prefix:          " f"{ip_edge_count:,}")
    print(f"shares_coupon:             " f"{coupon_edge_count:,}")

    print(f"\nRare coupons:              " f"{len(rare_coupons):,}")

    # --------------------------------------------------------
    # 7. Build graph
    # --------------------------------------------------------

    account_ids = accounts["account_id"].tolist()

    graph = build_graph(
        account_ids,
        edge_df,
    )

    graph_integrity_report(graph)

    # --------------------------------------------------------
    # 8. Louvain
    # --------------------------------------------------------

    (
        community_df,
        community_sizes,
    ) = run_louvain(graph)

    community_df.to_csv(
        COMMUNITIES_PATH,
        index=False,
    )

    print(f"\nCommunities saved to:\n" f"{COMMUNITIES_PATH}")

    # --------------------------------------------------------
    # 9. Node graph features
    # --------------------------------------------------------

    print("\nComputing node-level graph features...")

    graph_features = compute_node_graph_features(graph)

    # --------------------------------------------------------
    # Community aggregates
    # --------------------------------------------------------

    print("Computing community-level aggregates...")

    community_features = compute_community_features(
        features,
        community_df,
    )

    # --------------------------------------------------------
    # 10. Merge with Day 4
    # --------------------------------------------------------

    final_features = build_final_features(
        features,
        graph_features,
        community_features,
    )

    final_features.to_csv(
        FEATURES_GRAPH_PATH,
        index=False,
    )

    print(f"\nCombined graph features saved to:\n" f"{FEATURES_GRAPH_PATH}")

    # --------------------------------------------------------
    # 11. Locked baseline
    #
    # Ground truth has NOT been loaded.
    # --------------------------------------------------------

    print("\nApplying locked rule baseline...")

    predictions = apply_locked_baseline_rules(final_features)

    # --------------------------------------------------------
    # 12. Evaluation
    #
    # Ground truth is loaded for the first time here.
    # --------------------------------------------------------

    print("\nEvaluating against ground truth...")

    (
        metrics,
        evaluation,
    ) = evaluate_baseline(predictions)

    print_baseline_results(
        metrics,
        predictions,
    )

    # --------------------------------------------------------
    # 13. Save baseline metrics
    # --------------------------------------------------------

    save_baseline_metrics(metrics)

    # --------------------------------------------------------
    # 14. Leakage report
    # --------------------------------------------------------

    write_day5_leakage_report(
        filtered_orders,
        filtered_devices,
        filtered_addresses,
        filtered_phones,
        filtered_instruments,
        coupon_counts,
        graph,
        final_features,
    )

    # --------------------------------------------------------
    # Stop-condition checks
    # --------------------------------------------------------

    print("\n===================================")
    print("DAY 5 STOP-CONDITION")
    print("===================================")

    precision = metrics["precision"]
    recall = metrics["recall"]

    stop_condition_passed = True

    if len(final_features) != len(features):
        stop_condition_passed = False

    if final_features.isna().sum().sum() != 0:
        stop_condition_passed = False

    if precision <= 0 or precision >= 1:
        print("STOP: Precision is trivial " f"({precision:.4f}).")
        stop_condition_passed = False

    if recall <= 0 or recall >= 1:
        print("STOP: Recall is trivial " f"({recall:.4f}).")
        stop_condition_passed = False

    if metrics["true_ring_members_caught"] == 0:
        print("STOP: No true ring members were caught.")
        stop_condition_passed = False

    if metrics["total_flagged"] == 0:
        print("STOP: No accounts were flagged.")
        stop_condition_passed = False

    if stop_condition_passed:
        print("\nDAY 5 PASSED.")
        print("Ready for Day 6–7 LightGBM.")
    else:
        print("\nDAY 5 DID NOT PASS.")
        print("Do not proceed to LightGBM.")
        print(
            "Investigate graph structure, " "feature distributions, and locked rules."
        )

        raise RuntimeError("Day 5 stop condition failed.")


if __name__ == "__main__":
    main()
