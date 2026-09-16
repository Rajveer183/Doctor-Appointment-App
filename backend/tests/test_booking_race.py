import asyncio


async def test_concurrent_booking_only_one_request_succeeds(client_with_seed):
    client, ids = client_with_seed

    payload_a = {"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "race A"}
    payload_b = {"slot_id": ids["slot_id"], "patient_id": ids["patient_b"], "reason": "race B"}

    response_a, response_b = await asyncio.gather(
        client.post("/api/appointments", json=payload_a),
        client.post("/api/appointments", json=payload_b),
    )

    statuses = sorted([response_a.status_code, response_b.status_code])
    assert statuses == [201, 409], f"expected exactly one booking to win, got {statuses}"

    winner = response_a if response_a.status_code == 201 else response_b
    assert winner.json()["slot_id"] == ids["slot_id"]

    patient_a_appts = (await client.get(f"/api/patients/{ids['patient_a']}/appointments")).json()
    patient_b_appts = (await client.get(f"/api/patients/{ids['patient_b']}/appointments")).json()
    total_confirmed = len(patient_a_appts) + len(patient_b_appts)
    assert total_confirmed == 1, "the losing request must not have created an appointment row"


async def test_sequential_double_booking_returns_409(client_with_seed):
    client, ids = client_with_seed

    first = await client.post(
        "/api/appointments",
        json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "first"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/appointments",
        json={"slot_id": ids["slot_id"], "patient_id": ids["patient_b"], "reason": "second"},
    )
    assert second.status_code == 409
