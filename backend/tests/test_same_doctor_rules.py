async def test_cannot_book_same_doctor_twice_same_day(client_with_seed):
    client, ids = client_with_seed

    first = await client.post(
        "/api/appointments", json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "morning"}
    )
    assert first.status_code == 201

    # Different, non-overlapping time later the same day, same doctor — still rejected.
    second = await client.post(
        "/api/appointments", json={"slot_id": ids["same_day_slot_id"], "patient_id": ids["patient_a"], "reason": "afternoon"}
    )
    assert second.status_code == 409
    assert "already have an appointment with this doctor on this day" in second.json()["detail"].lower()


async def test_different_patients_can_each_book_same_doctor_same_day(client_with_seed):
    client, ids = client_with_seed

    first = await client.post(
        "/api/appointments", json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "a"}
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/appointments", json={"slot_id": ids["same_day_slot_id"], "patient_id": ids["patient_b"], "reason": "b"}
    )
    assert second.status_code == 201


async def test_same_patient_can_book_same_doctor_on_a_different_day(client_with_seed):
    client, ids = client_with_seed

    first = await client.post(
        "/api/appointments", json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "a"}
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/appointments", json={"slot_id": ids["non_overlapping_slot_id"], "patient_id": ids["patient_a"], "reason": "b"}
    )
    assert second.status_code == 201


async def test_doctor_cannot_have_two_confirmed_appointments_at_the_same_time(client_with_seed):
    client, ids = client_with_seed

    first = await client.post(
        "/api/appointments", json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "a"}
    )
    assert first.status_code == 201

    # Different patient, different Slot row, but same doctor + same exact time.
    second = await client.post(
        "/api/appointments",
        json={"slot_id": ids["doctor_duplicate_time_slot_id"], "patient_id": ids["patient_b"], "reason": "b"},
    )
    assert second.status_code == 409
    assert "already has another appointment" in second.json()["detail"].lower()
