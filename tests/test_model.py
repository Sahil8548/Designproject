"""Test suite for model loading and scoring."""
import numpy as np
import pytest
from unitime_app.model_loader import load_trained_model, score_candidate_features
from unitime_app.data_loader import load_candidate_features


def test_model_loading():
    model = load_trained_model()
    assert model is not None
    assert hasattr(model, "predict_proba")


def test_candidate_scoring():
    features = load_candidate_features().head(100)
    scores = score_candidate_features(features)
    assert len(scores) == 100
    assert isinstance(scores, np.ndarray)
    assert (scores >= 0.0).all() and (scores <= 1.0).all()
