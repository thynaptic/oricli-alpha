import pytest
from mavaia_core.data.search import DatasetSearch, SearchResult

def test_ranking_logic():
    search = DatasetSearch()
    
    results = [
        SearchResult(id="ds1", name="Python code", source="huggingface", description="A dataset about Python", popularity_score=100),
        SearchResult(id="ds2", name="Java guide", source="huggingface", description="Helpful Java snippets", popularity_score=500),
        SearchResult(id="ds3", name="Python basics", source="wikipedia", description="Wikipedia article about Python", popularity_score=1),
    ]
    
    ranked = search.rank_results("Python", results)
    
    assert len(ranked) == 3
    # ds1 and ds3 should be higher than ds2 because of relevance to "Python"
    assert ranked[0].id in ["ds1", "ds3"]
    assert ranked[1].id in ["ds1", "ds3"]
    assert ranked[2].id == "ds2"

def test_search_huggingface_mock(mocker):
    # Mock HfApi
    mock_api = mocker.patch("huggingface_hub.HfApi")
    mock_instance = mock_api.return_value
    
    mock_ds = mocker.MagicMock()
    mock_ds.id = "user/python-dataset"
    mock_ds.downloads = 1000
    mock_ds.description = "Mock description"
    
    mock_instance.list_datasets.return_value = [mock_ds]
    
    search = DatasetSearch()
    results = search.search_huggingface("python")
    
    assert len(results) == 1
    assert results[0].id == "user/python-dataset"
    assert results[0].source == "huggingface"

def test_search_wikipedia_mock(mocker):
    mock_wiki = mocker.patch("wikipedia.search")
    mock_wiki.return_value = ["Python (programming language)"]
    
    search = DatasetSearch()
    results = search.search_wikipedia("python")
    
    assert len(results) == 1
    assert "Python" in results[0].name
    assert results[0].source == "wikipedia"
