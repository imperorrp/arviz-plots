"""dist plot code."""
import warnings
from copy import copy

import arviz_stats  # pylint: disable=unused-import
import xarray as xr
from arviz_base import rcParams
from arviz_base.labels import BaseLabeller

from arviz_plots.plot_collection import PlotCollection
from arviz_plots.plots.utils import filter_aes, process_group_variables_coords
from arviz_plots.visuals import (
    ecdf_line,
    labelled_title,
    line_x,
    line_xy,
    point_estimate_text,
    remove_axis,
    scatter_x,
)


def plot_dist(
    dt,
    var_names=None,
    filter_vars=None,
    group="posterior",
    coords=None,
    sample_dims=None,
    kind=None,
    point_estimate=None,
    ci_kind=None,
    ci_prob=None,
    plot_collection=None,
    backend=None,
    labeller=None,
    aes_map=None,
    plot_kwargs=None,
    stats_kwargs=None,
    pc_kwargs=None,
):
    """Plot 1D marginal densities in the style of John K. Kruschke’s book.

    Generate :term:`facetted` :term:`plots` with: a graphical representation of 1D marginal
    densities (as KDE, histogram, ECDF or dotplot), a credible interval and a point estimate.

    Parameters
    ----------
    dt : DataTree or dict of {str : DataTree}
        Input data. In case of dictionary input, the keys are taken to be model names.
        In such cases, a dimension "model" is generated and can be used to map to aesthetics.
    var_names : str or list of str, optional
        One or more variables to be plotted.
        Prefix the variables by ~ when you want to exclude them from the plot.
    filter_vars : {None, “like”, “regex”}, default=None
        If None, interpret var_names as the real variables names.
        If “like”, interpret var_names as substrings of the real variables names.
        If “regex”, interpret var_names as regular expressions on the real variables names.
    group : str, default "posterior"
        Group to be plotted.
    coords : dict, optional
    sample_dims : str or sequence of hashable, optional
        Dimensions to reduce unless mapped to an aesthetic.
        Defaults to ``rcParams["data.sample_dims"]``
    kind : {"kde", "hist", "dot", "ecdf"}, optional
        How to represent the marginal density.
        Defaults to ``rcParams["plot.density_kind"]``
    point_estimate : {"mean", "median", "mode"}, optional
        Which point estimate to plot. Defaults to rcParam :data:`stats.point_estimate`
    ci_kind : {"eti", "hdi"}, optional
        Which credible interval to use. Defaults to ``rcParams["stats.ci_kind"]``
    ci_prob : float, optional
        Indicates the probability that should be contained within the plotted credible interval.
        Defaults to ``rcParams["stats.ci_prob"]``
    plot_collection : PlotCollection, optional
    backend : {"matplotlib", "bokeh"}, optional
    labeller : labeller, optional
    aes_map : mapping of {str : sequence of str}, optional
        Mapping of artists to aesthetics that should use their mapping in `plot_collection`
        when plotted. Valid keys are the same as for `plot_kwargs`.

        With a single model, no aesthetic mappings are generated by default,
        each variable+coord combination gets a :term:`plot` but they all look the same,
        unless there are user provided aesthetic mappings.
        With multiple models, ``plot_dist`` maps "color" and "y" to the "model" dimension.

        By default, all aesthetics but "y" are mapped to the density representation,
        and if multiple models are present, "color" and "y" are mapped to the
        credible interval and the point estimate.

        When "point_estimate" key is provided but "point_estimate_text" isn't,
        the values assigned to the first are also used for the second.
    plot_kwargs : mapping of {str : mapping or False}, optional
        Valid keys are:

        * One of "kde", "ecdf", "dot" or "hist", matching the `kind` argument.

          * "kde" -> passed to :func:`~arviz_plots.visuals.line_xy`
          * "ecdf" -> passed to :func:`~arviz_plots.visuals.ecdf_line`
          * "hist" -> passed to :func: `~WIP`

        * credible_interval -> passed to :func:`~arviz_plots.visuals.line_x`
        * point_estimate -> passed to :func:`~arviz_plots.visuals.scatter_x`
        * point_estimate_text -> passed to :func:`~arviz_plots.visuals.point_estimate_text`
        * title -> passed to :func:`~arviz_plots.visuals.labelled_title`
        * remove_axis -> not passed anywhere, can only be ``False`` to skip calling this function

    stats_kwargs : mapping, optional
        Valid keys are:

        * density -> passed to kde, ecdf, ...
        * credible_interval -> passed to eti or hdi
        * point_estimate -> passed to mean, median or mode

    pc_kwargs : mapping
        Passed to :class:`arviz_plots.PlotCollection.wrap`

    Returns
    -------
    PlotCollection

    Examples
    --------
    The following examples focus on behaviour specific to ``plot_dist``.
    For a general introduction to batteries-included functions like this one and common
    usage examples see :ref:`plots_intro`

    Default plot_dist for a single model:

    .. plot::
        :context: close-figs

        >>> from arviz_plots import plot_dist, style
        >>> style.use("arviz-clean")
        >>> from arviz_base import load_arviz_data
        >>> centered = load_arviz_data('centered_eight')
        >>> non_centered = load_arviz_data('non_centered_eight')
        >>> pc = plot_dist(centered)

    Default plot_dist for multiple models:

    .. plot::
        :context: close-figs

        >>> pc = plot_dist(
        >>>     {"centered": centered, "non centered": non_centered},
        >>>     coords={"school": ["Choate", "Deerfield", "Hotchkiss"]},
        >>> )
        >>> pc.add_legend("model")

    We can also manually map the color to the variable, and have the mapping apply
    to the title too instead of only the density representation:

    .. plot::
        :context: close-figs

        >>> pc = plot_dist(
        >>>     non_centered,
        >>>     coords={"school": ["Choate", "Deerfield", "Hotchkiss"]},
        >>>     pc_kwargs={"aes": {"color": ["__variable__"]}},
        >>>     aes_map={"title": ["color"]},
        >>> )

    """
    if ci_kind not in ("hdi", "eti", None):
        raise ValueError("ci_kind must be either 'hdi' or 'eti'")

    if sample_dims is None:
        sample_dims = rcParams["data.sample_dims"]
    if isinstance(sample_dims, str):
        sample_dims = [sample_dims]
    if ci_prob is None:
        ci_prob = rcParams["stats.ci_prob"]
    if ci_kind is None:
        ci_kind = rcParams["stats.ci_kind"] if "stats.ci_kind" in rcParams else "eti"
    if point_estimate is None:
        point_estimate = rcParams["stats.point_estimate"]
    if kind is None:
        kind = rcParams["plot.density_kind"]
    if plot_kwargs is None:
        plot_kwargs = {}
    if pc_kwargs is None:
        pc_kwargs = {}
    else:
        pc_kwargs = pc_kwargs.copy()

    if stats_kwargs is None:
        stats_kwargs = {}

    distribution = process_group_variables_coords(
        dt, group=group, var_names=var_names, filter_vars=filter_vars, coords=coords
    )

    if plot_collection is None:
        if backend is None:
            backend = rcParams["plot.backend"]
        pc_kwargs.setdefault("col_wrap", 5)
        pc_kwargs.setdefault(
            "cols",
            ["__variable__"]
            + [dim for dim in distribution.dims if dim not in {"model"}.union(sample_dims)],
        )
        if "model" in distribution:
            pc_kwargs["aes"] = pc_kwargs.get("aes", {}).copy()
            pc_kwargs["aes"].setdefault("color", ["model"])
            pc_kwargs["aes"].setdefault("y", ["model"])
        plot_collection = PlotCollection.wrap(
            distribution,
            backend=backend,
            **pc_kwargs,
        )

    if aes_map is None:
        aes_map = {}
    else:
        aes_map = aes_map.copy()
    aes_map.setdefault(kind, plot_collection.aes_set.difference("y"))
    if "model" in distribution:
        aes_map.setdefault("credible_interval", ["color", "y"])
        aes_map.setdefault("point_estimate", ["color", "y"])
    if "point_estimate" in aes_map and "point_estimate_text" not in aes_map:
        aes_map["point_estimate_text"] = aes_map["point_estimate"]
    if labeller is None:
        labeller = BaseLabeller()

    # density
    density_kwargs = copy(plot_kwargs.get(kind, {}))

    if density_kwargs is not False:
        density_dims, _, density_ignore = filter_aes(plot_collection, aes_map, kind, sample_dims)
        if kind == "kde":
            with warnings.catch_warnings():
                if "model" in distribution:
                    warnings.filterwarnings("ignore", message="Your data appears to have a single")
                density = distribution.azstats.kde(
                    dims=density_dims, **stats_kwargs.get("density", {})
                )
            plot_collection.map(
                line_xy, "kde", data=density, ignore_aes=density_ignore, **density_kwargs
            )

        elif kind == "ecdf":
            density = distribution.azstats.ecdf(
                dims=density_dims, **stats_kwargs.get("density", {})
            )
            plot_collection.map(
                ecdf_line,
                "ecdf",
                data=density,
                ignore_aes=density_ignore,
                **density_kwargs,
            )

        # elif kind == "hist":
        # WIP

        else:
            raise NotImplementedError("coming soon")

    if (
        (density_kwargs is not None)
        and ("model" in distribution)
        and (plot_collection.coords is None)
    ):
        reduce_dim_map = {"kde": "kde_dim", "ecdf": "quantile"}
        y_ds = plot_collection.get_aes_as_dataset("y")
        y_ds = (
            0.15 * y_ds * density.sel(plot_axis="y", drop=True).max([reduce_dim_map[kind], "model"])
        )
        plot_collection.update_aes_from_dataset("y", y_ds)

    # credible interval
    ci_kwargs = copy(plot_kwargs.get("credible_interval", {}))
    if ci_kwargs is not False:
        ci_dims, ci_aes, ci_ignore = filter_aes(
            plot_collection, aes_map, "credible_interval", sample_dims
        )
        if ci_kind == "eti":
            ci = distribution.azstats.eti(
                prob=ci_prob, dims=ci_dims, **stats_kwargs.get("credible_interval", {})
            )
        elif ci_kind == "hdi":
            ci = distribution.azstats.hdi(
                prob=ci_prob, dims=ci_dims, **stats_kwargs.get("credible_interval", {})
            )

        if "color" not in ci_aes:
            ci_kwargs.setdefault("color", "gray")
        plot_collection.map(line_x, "credible_interval", data=ci, ignore_aes=ci_ignore, **ci_kwargs)

    # point estimate
    pe_kwargs = copy(plot_kwargs.get("point_estimate", {}))
    pet_kwargs = copy(plot_kwargs.get("point_estimate_text", {}))
    if (pe_kwargs is not False) or (pet_kwargs is not False):
        pe_dims, pe_aes, pe_ignore = filter_aes(
            plot_collection, aes_map, "point_estimate", sample_dims
        )
        if point_estimate == "median":
            point = distribution.median(dim=pe_dims, **stats_kwargs.get("point_estimate", {}))
        elif point_estimate == "mean":
            point = distribution.mean(dim=pe_dims, **stats_kwargs.get("point_estimate", {}))
        else:
            raise NotImplementedError("coming soon")

    if pe_kwargs is not False:
        if "color" not in pe_aes:
            pe_kwargs.setdefault("color", "gray")
        plot_collection.map(
            scatter_x,
            "point_estimate",
            data=point,
            ignore_aes=pe_ignore,
            **pe_kwargs,
        )
    if pet_kwargs is not False:
        if density_kwargs is False:
            point_y = xr.ones_like(point)
        elif kind == "kde":
            point_density_diff = [
                dim for dim in density.sel(plot_axis="y").dims if dim not in point.dims
            ]
            point_density_diff = ["kde_dim"] + point_density_diff
            point_y = 0.04 * density.sel(plot_axis="y", drop=True).max(dim=point_density_diff)
        elif kind == "ecdf":
            # ecdf max is always 1
            point_y = xr.full_like(point, 0.04)

        point = xr.concat((point, point_y), dim="plot_axis").assign_coords(plot_axis=["x", "y"])
        _, pet_aes, pet_ignore = filter_aes(
            plot_collection, aes_map, "point_estimate_text", sample_dims
        )
        if "color" not in pet_aes:
            pet_kwargs.setdefault("color", "gray")
        pet_kwargs.setdefault("horizontal_align", "center")
        pet_kwargs.setdefault("point_label", "x")
        plot_collection.map(
            point_estimate_text,
            "point_estimate_text",
            data=point,
            point_estimate=point_estimate,
            ignore_aes=pet_ignore,
            **pet_kwargs,
        )

    # aesthetics
    title_kwargs = copy(plot_kwargs.get("title", {}))
    if title_kwargs is not False:
        _, title_aes, title_ignore = filter_aes(plot_collection, aes_map, "title", sample_dims)
        if "color" not in title_aes:
            title_kwargs.setdefault("color", "black")
        plot_collection.map(
            labelled_title,
            "title",
            ignore_aes=title_ignore,
            subset_info=True,
            labeller=labeller,
            **title_kwargs,
        )
    if (kind == "kde") and (plot_kwargs.get("remove_axis", True) is not False):
        plot_collection.map(
            remove_axis, store_artist=False, axis="y", ignore_aes=plot_collection.aes_set
        )

    return plot_collection
