# Testing

## How to run the test suite

To run the test suite `tox` should be installed.

### Run the whole test suite
Tox creates an independent env where all testing dependencies are installed
and then runs pytest to execute all tests on the `/test`:

```console
tox -e py311
```

The `-e` flag stands for "execute" we want to execute a previously defined job that
takes care of the steps above. The job name is "py" followed by your local python
version without decimal point.

:::{note}
It is also possible to run `pytest tests/` directly instead of `tox -e py311`,
and all commands covered in this page work either way. However, it is recommended
to use tox to isolate the testing environment and have local testing be as similar
as possible as testing in CI jobs.
:::

### Pass arguments to pytest
We can also pass arguments through tox to pytest. With this we can for example
select specific subsets of tests to be executed with the `-k` flag:

```console
tox -e py311 -- -k plot_trace_dist
```

Would run all tests whose name contains `plot_trace_dist`.
The [pytest documentation](https://docs.pytest.org/en/stable/reference/reference.html#command-line-flags)
lists and describes all available options.

### Custom pytest arguments
In addition to built-in pytest arguments, we have also defined a couple extra flags
in `tests/conftest.py` to handle arviz-plots specific situations.

#### Skip flags
One of the drivers of arviz-plots design is ensuring parity between the different
plotting backends with minimal duplication.

Therefore, all tests that depend on the plotting backend should be parametrized
with `@pytest.mark.parametrize("backend", backend_list)` to make sure all backends
pass all relevant tests.

At the same time however, arviz-plots considers all backends optional dependencies,
so not all backends might be installed and consequently, not all tests can be executed.
By default, testing works under the assumption that all backends are installed,
but backend specific tests can be skipped when running the test suite:

```console
tox -e py311 -- --skip-bokeh
tox -e py311 -- --skip-mpl
```

:::{note} It is also possible to use both flags, in which case, only tests
independent of the plotting backend like asethetic generation and the like
will be executed.
:::

#### Saving matplotlib figures generated by tests
Testing checks plotting functions can be executed and return objects with the
right properties, but there are no checks against the actual generated images.

As we might often want to check the generated images, there is also a `--save`
flag to indicate pytest to save all figures generated by matplotlib while testing.

This flag takes one optional argument in case we want to specify the folder where
the images will be saved, otherwise it defaults to `test_images` in the project
home folder.

```console
tox -e py311 -- --save
```

Generates basically the same output as any test job:

```
build: _optional_hooks> python ...
[...]
  py311: OK (42.26=setup[1.79]+cmd[40.47] seconds)
  congratulations :) (42.31 seconds)
```

But if you inspect the project home folder, you should see a `/test_images` folder
with contents similar to:

```
'test_grid[matplotlib].png'                            'test_plot_forest_extendable[matplotlib].png'        'test_plot_trace_dist[True-False-matplotlib].png'
'test_grid_rows_cols[cols-matplotlib].png'             'test_plot_forest[False-matplotlib].png'             'test_plot_trace_dist[True-True-matplotlib].png'
'test_grid_rows_cols[rows-matplotlib].png'             'test_plot_forest_models[matplotlib].png'            'test_plot_trace[matplotlib].png'
'test_grid_scalar[matplotlib].png'                     'test_plot_forest_sample[matplotlib].png'            'test_plot_trace_sample[matplotlib].png'
'test_grid_variable[matplotlib].png'                   'test_plot_forest[True-matplotlib].png'              'test_wrap[matplotlib].png'
'test_plot_dist[matplotlib].png'                       'test_plot_trace_dist[False-False-matplotlib].png'   'test_wrap_only_variable[matplotlib].png'
'test_plot_dist_models[matplotlib].png'                'test_plot_trace_dist[False-True-matplotlib].png'    'test_wrap_variable[matplotlib].png'
```

## About arviz-plots testing