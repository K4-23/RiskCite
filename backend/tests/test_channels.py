from app.pipeline.channels import CHANNELS, all_agents


def test_all_agents_fixed():
    agents = all_agents()
    assert agents == list(CHANNELS.keys())
    assert len(agents) == 10
    assert agents == all_agents()


def test_channel_registry_complete():
    assert len(CHANNELS) == 10
    for cid, channel in CHANNELS.items():
        assert channel["name"] and channel["retrieval_queries"] and channel["checklist"] and channel["fallback"]
