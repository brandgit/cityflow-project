"""Processors module"""
from .base_processor import BaseProcessor
from .bikes_processor import BikesProcessor
from .traffic_processor import TrafficProcessor
from .weather_processor import WeatherProcessor
from .comptages_processor import ComptagesProcessor
from .chantiers_processor import ChantiersProcessor
from .referentiel_processor import ReferentielProcessor

__all__ = [
    'BaseProcessor',
    'BikesProcessor',
    'TrafficProcessor',
    'WeatherProcessor',
    'ComptagesProcessor',
    'ChantiersProcessor',
    'ReferentielProcessor'
]

