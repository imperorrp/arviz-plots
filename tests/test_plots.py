# pylint: disable=no-self-use, redefined-outer-name
"""Test batteries-included plots."""
import numpy as np
import pandas as pd
import pytest
from arviz_base import from_dict

from arviz_plots import (
    plot_compare,
    plot_dist,
    plot_forest,
    plot_ppc,
    plot_ridge,
    plot_trace,
    plot_trace_dist,
    visuals,
)

pytestmark = [
    pytest.mark.usefixtures("clean_plots"),
    pytest.mark.usefixtures("check_skips"),
    pytest.mark.usefixtures("no_artist_kwargs"),
]


@pytest.fixture(scope="module")
def datatree(seed=31):
    rng = np.random.default_rng(seed)
    mu = rng.normal(size=(4, 100))
    tau = rng.normal(size=(4, 100))
    theta = rng.normal(size=(4, 100, 7))
    diverging = rng.choice([True, False], size=(4, 100), p=[0.1, 0.9])
    obs = rng.normal(size=7)
    prior_predictive = rng.normal(size=(1, 100, 7))  # assuming 1 chain
    posterior_predictive = rng.normal(size=(4, 100, 7))

    return from_dict(
        {
            "posterior": {"mu": mu, "theta": theta, "tau": tau},
            "sample_stats": {"diverging": diverging},
            "observed_data": {"obs": obs},
            "prior_predictive": {"obs": prior_predictive},
            "posterior_predictive": {"obs": posterior_predictive},
        },
        dims={"theta": ["hierarchy"], "obs": ["hierarchy"]},
    )


@pytest.fixture(scope="module")
def datatree2(seed=17):
    rng = np.random.default_rng(seed)
    mu = rng.normal(size=(4, 100))
    tau = rng.normal(size=(4, 100))
    theta = rng.normal(size=(4, 100, 7))
    theta_t = rng.normal(size=(4, 100, 7))
    diverging = rng.choice([True, False], size=(4, 100), p=[0.1, 0.9])

    return from_dict(
        {
            "posterior": {"mu": mu, "theta": theta, "tau": tau, "theta_t": theta_t},
            "sample_stats": {"diverging": diverging},
        },
        dims={"theta": ["hierarchy"], "theta_t": ["hierarchy"]},
    )


@pytest.fixture(scope="module")
def datatree_4d(seed=31):
    rng = np.random.default_rng(seed)
    mu = rng.normal(size=(4, 100))
    theta = rng.normal(size=(4, 100, 5))
    eta = rng.normal(size=(4, 100, 5, 3))
    diverging = rng.choice([True, False], size=(4, 100), p=[0.1, 0.9])
    obs = rng.normal(size=(5, 3))  # hierarchy, group dims respectively
    prior_predictive = rng.normal(size=(1, 100, 5, 3))  # assuming 1 chain
    posterior_predictive = rng.normal(size=(4, 100, 5, 3))  # all chains

    return from_dict(
        {
            "posterior": {"mu": mu, "theta": theta, "eta": eta},
            "sample_stats": {"diverging": diverging},
            "observed_data": {"obs": obs},
            "prior_predictive": {"obs": prior_predictive},
            "posterior_predictive": {"obs": posterior_predictive},
        },
        dims={"theta": ["hierarchy"], "eta": ["hierarchy", "group"], "obs": ["hierarchy", "group"]},
    )


@pytest.fixture(scope="module")
def datatree_sample(seed=31):
    rng = np.random.default_rng(seed)
    mu = rng.normal(size=100)
    tau = rng.normal(size=100)
    theta = rng.normal(size=(100, 7))
    diverging = rng.choice([True, False], size=100, p=[0.1, 0.9])
    obs = rng.normal(size=7)
    prior_predictive = rng.normal(size=(10, 7))  # assuming 10 prior predictive samples
    posterior_predictive = rng.normal(size=(100, 7))

    return from_dict(
        {
            "posterior": {"mu": mu, "theta": theta, "tau": tau},
            "sample_stats": {"diverging": diverging},
            "observed_data": {"obs": obs},
            "prior_predictive": {"obs": prior_predictive},
            "posterior_predictive": {"obs": posterior_predictive},
        },
        dims={"theta": ["hierarchy"]},
        sample_dims=["sample"],
    )


@pytest.fixture(scope="module")
def cmp():
    return pd.DataFrame(
        {
            "elpd_loo": [-4.5, -14.3, -16.2],
            "p_loo": [2.6, 2.3, 2.1],
            "elpd_diff": [0, 9.7, 11.3],
            "weight": [0.9, 0.1, 0],
            "se": [2.3, 2.7, 2.3],
            "dse": [0, 2.7, 2.3],
            "warning": [False, False, False],
            "scale": ["log", "log", "log"],
        },
        index=["Model B", "Model A", "Model C"],
    )


@pytest.mark.parametrize("backend", ["matplotlib", "bokeh", "plotly", "none"])
class TestPlots:
    @pytest.mark.parametrize("kind", ["kde", "hist", "ecdf"])
    def test_plot_dist(self, datatree, backend, kind):
        pc = plot_dist(datatree, backend=backend, kind=kind)
        assert not pc.aes["mu"]
        assert kind in pc.viz["mu"]
        assert "hierarchy" not in pc.viz["mu"].dims
        assert "hierarchy" in pc.viz["theta"].dims
        assert "hierarchy" not in pc.viz["mu"]["point_estimate"].dims
        assert "hierarchy" in pc.viz["theta"]["point_estimate"].dims

    @pytest.mark.parametrize("kind", ["kde", "hist", "ecdf"])
    def test_plot_dist_sample(self, datatree_sample, backend, kind):
        pc = plot_dist(datatree_sample, backend=backend, sample_dims="sample", kind=kind)
        assert not pc.aes["mu"]
        assert kind in pc.viz["mu"]
        assert "hierarchy" not in pc.viz["mu"].dims
        assert "hierarchy" in pc.viz["theta"].dims
        assert "hierarchy" not in pc.viz["mu"]["point_estimate"].dims
        assert "hierarchy" in pc.viz["theta"]["point_estimate"].dims

    @pytest.mark.parametrize("kind", ["kde"])
    def test_plot_dist_models(self, datatree, datatree2, backend, kind):
        pc = plot_dist({"c": datatree, "n": datatree2}, backend=backend, kind=kind)
        assert "/mu" in pc.aes.groups
        assert "/mu" in pc.viz.groups
        assert kind in pc.viz["mu"].data_vars
        assert "hierarchy" not in pc.viz["mu"].dims
        assert "model" in pc.viz["mu"].dims

    def test_plot_trace(self, datatree, backend):
        pc = plot_trace(datatree, backend=backend)
        assert "chart" in pc.viz.data_vars
        assert "plot" not in pc.viz.data_vars
        assert pc.viz["mu"].trace.shape == (4,)

    def test_plot_trace_sample(self, datatree_sample, backend):
        pc = plot_trace(datatree_sample, sample_dims="sample", backend=backend)
        assert "chart" in pc.viz.data_vars
        assert "plot" not in pc.viz.data_vars
        assert pc.viz["mu"].trace.shape == ()

    @pytest.mark.parametrize("compact", (True, False))
    @pytest.mark.parametrize("combined", (True, False))
    def test_plot_trace_dist(self, datatree, backend, compact, combined):
        kind = "kde"
        pc = plot_trace_dist(datatree, backend=backend, compact=compact, combined=combined)
        assert "chart" in pc.viz.data_vars
        assert "plot" not in pc.viz.data_vars
        assert "chain" in pc.viz["theta"]["trace"].dims
        if combined:
            assert "chain" not in pc.viz["theta"][kind].dims
        else:
            assert "chain" in pc.viz["theta"][kind].dims
        if compact:
            assert "hierarchy" not in pc.viz["theta"]["plot"].dims
        else:
            assert "hierarchy" in pc.viz["theta"]["plot"].dims

    @pytest.mark.parametrize("compact", (True, False))
    def test_plot_trace_dist_sample(self, datatree_sample, backend, compact):
        pc = plot_trace_dist(
            datatree_sample, backend=backend, sample_dims="sample", compact=compact
        )
        assert "chart" in pc.viz.data_vars
        assert "plot" not in pc.viz.data_vars
        if compact:
            assert "hierarchy" not in pc.viz["theta"]["plot"].dims
        else:
            assert "hierarchy" in pc.viz["theta"]["plot"].dims

    @pytest.mark.parametrize("combined", (True, False))
    def test_plot_forest(self, datatree, backend, combined):
        pc = plot_forest(datatree, backend=backend, combined=combined)
        assert "plot" in pc.viz.data_vars
        assert all("y" in child.data_vars for child in pc.aes.children.values())

    def test_plot_forest_sample(self, datatree_sample, backend):
        pc = plot_forest(datatree_sample, backend=backend, sample_dims="sample")
        assert "plot" in pc.viz.data_vars

    def test_plot_forest_models(self, datatree, datatree2, backend):
        pc = plot_forest({"c": datatree, "n": datatree2}, backend=backend)
        assert "plot" in pc.viz.data_vars

    def test_plot_forest_extendable(self, datatree, backend):
        dt_aux = (
            datatree["posterior"]
            .expand_dims(column=3)
            .assign_coords(column=["labels", "forest", "ess"])
        )
        pc = plot_forest(dt_aux, combined=True, backend=backend)
        mock_ess = datatree["posterior"].ds.mean(("chain", "draw"))
        pc.map(visuals.scatter_x, "ess", data=mock_ess, coords={"column": "ess"}, color="blue")
        assert "plot" in pc.viz.data_vars
        assert pc.viz["plot"].sizes["column"] == 3
        assert all("ess" in child.data_vars for child in pc.viz.children.values())

    @pytest.mark.parametrize("pseudo_dim", ("__variable__", "hierarchy", "group"))
    def test_plot_forest_aes_labels_shading(self, backend, datatree_4d, pseudo_dim):
        pc = plot_forest(
            datatree_4d,
            pc_kwargs={"aes": {"color": [pseudo_dim]}},
            aes_map={"labels": ["color"]},
            shade_label=pseudo_dim,
            backend=backend,
        )
        assert "plot" in pc.viz.data_vars
        assert all("shade" in child.data_vars for child in pc.viz.children.values())
        if pseudo_dim != "__variable__":
            assert all(0 in child["alpha"] for child in pc.aes.children.values())
            assert any(pseudo_dim in child["shade"].dims for child in pc.viz.children.values())

    @pytest.mark.parametrize("combined", (True, False))
    def test_plot_ridge(self, datatree, backend, combined):
        pc = plot_ridge(datatree, backend=backend, combined=combined)
        assert "plot" in pc.viz.data_vars
        assert all("y" in child.data_vars for child in pc.aes.children.values())
        assert "edge" in pc.viz["mu"]
        assert "hierarchy" not in pc.viz["mu"].dims
        assert "hierarchy" in pc.viz["theta"].dims

    def test_plot_ridge_sample(self, datatree_sample, backend):
        pc = plot_ridge(datatree_sample, backend=backend, sample_dims="sample")
        assert "plot" in pc.viz.data_vars
        assert "edge" in pc.viz["mu"]
        assert "hierarchy" not in pc.viz["mu"].dims
        assert "hierarchy" in pc.viz["theta"].dims

    def test_plot_ridge_models(self, datatree, datatree2, backend):
        pc = plot_ridge({"c": datatree, "n": datatree2}, backend=backend)
        assert "plot" in pc.viz.data_vars
        assert "/mu" in pc.aes.groups
        assert "/mu" in pc.viz.groups
        assert "edge" in pc.viz["mu"].data_vars
        assert "hierarchy" not in pc.viz["mu"].dims
        assert "model" in pc.viz["mu"].dims

    def test_plot_ridge_extendable(self, datatree, backend):
        dt_aux = (
            datatree["posterior"]
            .expand_dims(column=3)
            .assign_coords(column=["labels", "ridge", "ess"])
        )
        pc = plot_ridge(dt_aux, combined=True, backend=backend)
        mock_ess = datatree["posterior"].ds.mean(("chain", "draw"))
        pc.map(visuals.scatter_x, "ess", data=mock_ess, coords={"column": "ess"}, color="blue")
        assert "plot" in pc.viz.data_vars
        assert pc.viz["plot"].sizes["column"] == 3
        assert all("ess" in child.data_vars for child in pc.viz.children.values())

    @pytest.mark.parametrize("pseudo_dim", ("__variable__", "hierarchy", "group"))
    def test_plot_ridge_aes_labels_shading(self, backend, datatree_4d, pseudo_dim):
        pc = plot_forest(
            datatree_4d,
            pc_kwargs={"aes": {"color": [pseudo_dim]}},
            aes_map={"labels": ["color"]},
            shade_label=pseudo_dim,
            backend=backend,
        )
        assert "plot" in pc.viz.data_vars
        assert all("shade" in child.data_vars for child in pc.viz.children.values())
        if pseudo_dim != "__variable__":
            assert all(0 in child["alpha"] for child in pc.aes.children.values())
            assert any(pseudo_dim in child["shade"].dims for child in pc.viz.children.values())

    def test_plot_compare(self, cmp, backend):
        pc = plot_compare(cmp, backend=backend)
        assert pc.viz["plot"]

    def test_plot_compare_kwargs(self, cmp, backend):
        plot_compare(
            cmp,
            plot_kwargs={
                "shade": {"color": "black", "alpha": 0.2},
                "error_bar": {"color": "gray"},
                "point_estimate": {"color": "red", "marker": "|"},
            },
            pc_kwargs={"plot_grid_kws": {"figsize": (1000, 200)}},
            backend=backend,
        )

    @pytest.mark.parametrize("kind", ("kde", "cumulative"))
    def test_plot_ppc(self, datatree, kind, backend):
        pc = plot_ppc(datatree, kind=kind, backend=backend)
        assert "chart" in pc.viz.data_vars
        assert "obs" in pc.viz
        # assert "ppc_dim" in pc.viz["obs"].dims
        if kind == "kde":
            assert "kde" in pc.viz["obs"]
        elif kind == "cumulative":
            assert "ecdf" in pc.viz["obs"]
        assert "overlay" in pc.aes["obs"].data_vars

    @pytest.mark.parametrize("kind", ("kde", "cumulative"))
    def test_plot_ppc_sample(self, datatree_sample, kind, backend):
        pc = plot_ppc(datatree_sample, kind=kind, sample_dims="sample", backend=backend)
        assert "chart" in pc.viz.data_vars
        assert "obs" in pc.viz
        # assert "ppc_dim" in pc.viz["obs"].dims
        if kind == "kde":
            assert "kde" in pc.viz["obs"]
        elif kind == "cumulative":
            assert "ecdf" in pc.viz["obs"]
        assert "overlay" in pc.aes["obs"].data_vars

    @pytest.mark.parametrize("kind", ("kde", "cumulative"))
    @pytest.mark.parametrize("facet_dims", (["group"], ["hierarchy"], None))
    def test_plot_ppc_4d(self, datatree_4d, facet_dims, kind, backend):
        pc = plot_ppc(
            datatree_4d,
            facet_dims=facet_dims,
            kind=kind,
            observed_rug=True,
            backend=backend,
        )
        assert "chart" in pc.viz.data_vars
        assert "obs" in pc.viz
        # assert "ppc_dim" in pc.viz["obs"].dims
        if kind == "kde":
            assert "kde" in pc.viz["obs"]
        elif kind == "cumulative":
            assert "ecdf" in pc.viz["obs"]
        assert "overlay" in pc.aes["obs"].data_vars
        if facet_dims is not None:
            for dim in facet_dims:
                assert dim in pc.viz["obs"]["plot"].dims
