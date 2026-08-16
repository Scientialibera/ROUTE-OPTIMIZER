from route_optimizer.preference import learn_zone_transitions


def test_zone_transition_learning():
    route_data = {
        "R1": {"stops": {"A": {"zone_id": "Z1"}, "B": {"zone_id": "Z2"}, "C": {"zone_id": "Z2"}, "D": {"zone_id": "Z3"}}}
    }
    actual = {"R1": {"actual": {"A": 0, "B": 1, "C": 2, "D": 3}}}
    model = learn_zone_transitions(route_data, actual)
    assert model.probabilities["Z1"]["Z2"] == 1.0
    assert model.probabilities["Z2"]["Z3"] == 1.0
