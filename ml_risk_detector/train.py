import os
import sys
import json
import logging
 
sys.path.insert(0, os.path.dirname(__file__))
 
import numpy as np
from sklearn.model_selection import train_test_split
 
from data.dataset import generate_synthetic_dataset
from utils.feature_engineering import FeatureEngineer, CodeMetrics
from models.risk_detector import MLRiskDetector
from models.prioritizer import TestPrioritizer
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train")
 
 
