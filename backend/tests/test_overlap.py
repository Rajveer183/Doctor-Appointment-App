async def test_cannot_book_overlapping_slot_with_different_doctor(client_with_seed):
    client, ids = client_with_seed

    first = await client.post(
        "/api/appointments",
        json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "first"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/appointments",
        json={"slot_id": ids["overlapping_slot_id"], "patient_id": ids["patient_a"], "reason": "second"},
    )
    assert second.status_code == 409
    assert "overlap" in second.json()["detail"].lower()


async def test_different_patients_can_book_overlapping_slots(client_with_seed):
    client, ids = client_with_seed

    first = await client.post(
        "/api/appointments",
        json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "first"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/appointments",
        json={"slot_id": ids["overlapping_slot_id"], "patient_id": ids["patient_b"], "reason": "second"},
    )
    assert second.status_code == 201


async def test_same_patient_can_book_non_overlapping_slots(client_with_seed):
    client, ids = client_with_seed

    first = await client.post(
        "/api/appointments",
        json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "first"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/appointments",
        json={"slot_id": ids["non_overlapping_slot_id"], "patient_id": ids["patient_a"], "reason": "second"},
    )
    assert second.status_code == 201
