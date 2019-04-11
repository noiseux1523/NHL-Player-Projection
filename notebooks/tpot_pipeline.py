import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_selection import SelectPercentile, f_regression
from sklearn.linear_model import LassoLarsCV, RidgeCV
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline, make_union
from sklearn.preprocessing import MaxAbsScaler, PolynomialFeatures, StandardScaler
from tpot.builtins import StackingEstimator
from sklearn.preprocessing import FunctionTransformer
from copy import copy

# NOTE: Make sure that the class is labeled 'target' in the data file
tpot_data = pd.read_csv('PATH/TO/DATA/FILE', sep='COLUMN_SEPARATOR', dtype=np.float64)
features = tpot_data.drop('target', axis=1).values
training_features, testing_features, training_target, testing_target = \
            train_test_split(features, tpot_data['target'].values, random_state=None)

# Average CV score on the training set was:-109.53604510235976
exported_pipeline = make_pipeline(
    make_union(
        StackingEstimator(estimator=ExtraTreesRegressor(bootstrap=True, max_features=0.3, min_samples_leaf=11, min_samples_split=18, n_estimators=100)),
        make_pipeline(
            make_union(
                make_union(
                    make_union(
                        StackingEstimator(estimator=make_pipeline(
                            StandardScaler(),
                            SelectPercentile(score_func=f_regression, percentile=20),
                            MaxAbsScaler(),
                            RidgeCV()
                        )),
                        FunctionTransformer(copy)
                    ),
                    FunctionTransformer(copy)
                ),
                StandardScaler()
            ),
            MaxAbsScaler(),
            StackingEstimator(estimator=RidgeCV()),
            PolynomialFeatures(degree=2, include_bias=False, interaction_only=False)
        )
    ),
    LassoLarsCV(normalize=False)
)

exported_pipeline.fit(training_features, training_target)
results = exported_pipeline.predict(testing_features)
