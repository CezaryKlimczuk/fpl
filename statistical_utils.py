import os
import yaml
import numpy as np
from pathlib import Path
from typing import Iterable, Tuple
from scipy.stats import poisson, nbinom


def get_goal_data():
    _path = Path(os.path.abspath(__file__)).parent / "config" / "teams_goals.yaml"
    with open(_path) as f:
        team_goals = yaml.safe_load(f)
        f.close()
    return team_goals


def calculate_margin(odds_vector: Iterable[float]) -> float:
    if isinstance(odds_vector, list):
        odds_vector = np.array(odds_vector)
    return 1 / np.sum(1 / odds_vector)


def calculate_implied_prob(odds_vector: Iterable[float]) -> Iterable[float]:
    if isinstance(odds_vector, list):
        odds_vector = np.array(odds_vector)
    margin = calculate_margin(odds_vector)
    return margin / odds_vector


def calculate_odds(prob_vector: Iterable[float], margin: float = 0.95) -> Iterable[float]:
    if isinstance(prob_vector, list) or isinstance(prob_vector, tuple):
        prob_vector = np.array(prob_vector)
    return margin / prob_vector


def calculate_poisson_prob_vec(lambda_goals: float, depth: int = 11) -> Iterable[float]:
    return np.array([poisson.pmf(i, lambda_goals) for i in range(depth)])


def bivariate_poisson_sum(lambda_home, lambda_away, depth=11) -> Tuple:
    goals_home_vec = calculate_poisson_prob_vec(lambda_home, depth)
    goals_away_vec = calculate_poisson_prob_vec(lambda_away, depth)
    bivariate_probs = np.outer(goals_home_vec, goals_away_vec)
    draw_prob = np.sum(np.diag(bivariate_probs))
    away_prob = np.sum(np.triu(bivariate_probs)) - draw_prob
    home_prob = np.sum(np.tril(bivariate_probs)) - draw_prob
    return home_prob, draw_prob, away_prob