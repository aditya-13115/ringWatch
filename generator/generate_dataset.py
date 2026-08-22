from .entities import generate_all_entities
from .validate import validate_entities


def main():
    print("Generating RingWatch Day 1...")

    generate_all_entities()

    print("\nRunning validation...")
    validate_entities()

    print("\nDay 1 completed successfully.")


if __name__ == "__main__":
    main()