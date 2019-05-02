from pypuf.studies.base import Study
from pypuf import tools
from pypuf.learner.regression.logistic_regression import LogisticRegression
from pypuf.simulation.arbiter_based.ltfarray import LTFArray
from matplotlib.pyplot import figure
import seaborn as sns
import numpy as np
from pypuf.experiments.experiment.base import Experiment
from numpy.random import RandomState
from os import getpid
from typing import NamedTuple
from uuid import UUID
from scipy.special import comb


class HybridAccuracyParameters(NamedTuple):
    """
    Experiment parameters for LTFArray.eval benchmark.
    """
    n: int
    k: int
    N: int
    transform: str
    combiner: str
    seed_instance: int
    iteration_limit: int


class Result(NamedTuple):
    """
    Experiment result from LTFArray.eval benchmark.
    """
    experiment_id: UUID
    pid: int
    accuracy: float


class HybridAccuracyExperiment(Experiment):
    """
    Measures the time the logistic regression learner takes to learn a target.
    """

    def __init__(self, progress_log_prefix, parameters):
        super().__init__(progress_log_prefix, parameters)
        self.instance = None
        self.learner = None
        self.model = None

    def prepare(self):
        # change to not hardcoded
        k = self.parameters.k  # 2
        n = self.parameters.n  # 64
        N = self.parameters.N  # 1200
        transform = self.parameters.transform   # LTFArray.transform_id
        combiner = self.parameters.combiner  # LTFArray.combiner_xor
        iteration_limit = self.parameters.iteration_limit

        self.instance = LTFArray(
            weight_array=LTFArray.normal_weights(n=n, k=k),  # do not change, can be simulated by learner
            transform=transform,  # has to match learner, otherwise learner cannot match
            combiner=combiner,  # do not change
        )

        self.learner = LogisticRegression(
            t_set=tools.TrainingSetHybrid(instance=self.instance, N=N),
            n=comb(n, 2, exact=True),  # n choose k_original/k_new = 2
            k=k//2,  # k divided by 2, what if k is odd?
            transformation=self.instance.transform,
            combiner=self.instance.combiner,
            iteration_limit=iteration_limit,
            # convergence_decimals=4,
        )

    def run(self):
        self.model = self.learner.learn()

    def analyze(self):
        """
        Analyzes the learned result.
        """
        assert self.model is not None
        accuracy = 1.0 - tools.approx_dist_hybrid(
            self.instance,
            self.model,
            min(10000, 2 ** self.parameters.n),
            random_instance=RandomState(self.parameters.seed_instance),
        )

        return Result(
            experiment_id=self.id,
            pid=getpid(),
            accuracy=accuracy,
        )


class HybridAccuracy(Study):
    SAMPLE_SIZE = 100
    TRANSFORMS = ["id"]

    def __init__(self):
        super().__init__()

    def experiments(self):
        experiments = []

        experiments.extend([
                HybridAccuracyExperiment(
                    progress_log_prefix=None,
                    parameters=HybridAccuracyParameters(
                        n=64,
                        k=4,
                        N=120000,
                        # N=10000,
                        transform='id',
                        combiner='xor',
                        seed_instance=314159 + i,
                        iteration_limit=50,
                    )
                )
                for i in range(self.SAMPLE_SIZE)
            ])

        return experiments

    def plot(self):
        # prepare data
        data = self.experimenter.results['accuracy']
        print(len(data))
        print(data)

        # plot
        fig = figure()
        ax = fig.add_subplot(1, 1, 1)
        sns.set()
        # bins = np.linspace(0,1,10)
        ax = sns.distplot(data)         # , bins=bins)

        ax.set_xlabel('Accuracy')
        ax.set_ylabel('Count')
        fig.suptitle('pypuf Hybrid Attack Accuracy Results')
        fig.savefig('figures/hybrid_attack_accuracy', bbox_inches='tight', pad_inches=.5)