import uuid


def generate_reference(prefix="SUB"):

    unique_part = (
        uuid.uuid4()
        .hex[:20]
        .upper()
    )

    return (
        f"{prefix}-{unique_part}"
    )
