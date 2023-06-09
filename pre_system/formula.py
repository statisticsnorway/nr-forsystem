##################################
# Author: Magnus Kvåle Helliesen #
# mkh@ssb.no                     #
##################################

import pandas as pd
import numpy as np


class Formula:
    _baseyear = None

    def __init__(self, name):
        """
        Initialize a Formula instance.

        Parameters
        ----------
        name : str
            The name of the formula.

        Raises
        ------
        TypeError
            If `name` is not a string.
        """
        if isinstance(name, str) is False:
            raise TypeError('name must be str')
        self._name = name.lower()
        self._baseyear = None
        self._calls_on = None

    @property
    def name(self):
        return self._name

    @property
    def baseyear(self):
        return self._baseyear

    @property
    def what(self):
        return None

    @property
    def calls_on(self):
        return self._calls_on

    @baseyear.setter
    def baseyear(self, baseyear):
        if isinstance(baseyear, int) is False:
            raise TypeError('baseyear must be int')
        self._baseyear = baseyear

    def __repr__(self):
        return f'Formula: {self.name} = {self.what}'

    def info(self, i=0):
        what = self.what if len(self.what) <= 100 else '...'
        print(f'{" "*i}{self.name} = {what}')
        for _, val in self.calls_on.items():
            val.info(i+1)

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None):
        """
        Evaluate the formula using the provided data.

        Parameters
        ----------
        annual_df : pd.DataFrame
            The annual data used for evaluation.
        indicator_df : pd.DataFrame
            The indicator data used for evaluation.
        weight_df : pd.DataFrame, optional
            The weight data used for evaluation. Defaults to None.
        correction_df : pd.DataFrame, optional
            The correction data used for evaluation. Defaults to None.

        Raises
        ------
        ValueError
            If the base year is not set or is out of range for the provided data.
        TypeError
            If any of the input data is not a Pandas DataFrame.
        AttributeError
            If the index of any input DataFrame is not a Pandas PeriodIndex or if the frequency is incorrect.
        IndexError
            If the base year is out of range for any input DataFrame.
        """
        if self.baseyear is None:
            raise ValueError('baseyear is None')

        self._check_df('annual_df', annual_df, self.baseyear, 'a')
        self._check_df('indicator_df', indicator_df, self.baseyear)

        if weight_df is not None:
            self._check_df('weight_df', weight_df, self.baseyear, 'a')

        if correction_df is not None:
            self._check_df('correction_df', correction_df, self.baseyear, indicator_df.index.freq)

    @staticmethod
    def _check_df(df_name, df, baseyear, frequency=None):
        """
        """
        if isinstance(df, pd.DataFrame) is False:
            raise TypeError(f'{df_name} must be a Pandas.DataFrame')
        if isinstance(df.index, pd.PeriodIndex) is False:
            raise AttributeError(f'{df_name}.index must be Pandas.PeriodIndex')
        if frequency and df.index.freq != frequency:
            raise AttributeError(f'{df_name} must have frequency {frequency}')
        if df[df.index.year == baseyear].shape[0] == 0:
            raise IndexError(f'baseyear {baseyear} is out of range for annual_df')
        if all(np.issubdtype(df[x].dtype, np.number) for x in df.columns) is False:
            raise TypeError(f'All columns in {df_name} must be numeric')


class Indicator(Formula):
    def __init__(self,
                 name: str,
                 annual_name: str,
                 indicator_names: list[str],
                 weight_names: list[str] = None,
                 correction_name: str = None,
                 aggregation: str = 'sum'):
        """
        Initialize an Indicator object.

        Parameters
        ----------
        name : str
            The name of the indicator.
        annual_name : str
            The name of the annual data.
        indicator_names : list[str]
            The list of indicator names.
        weight_names : list[str], optional
            The list of weight names, by default None.
        correction_name : str, optional
            The name of the correction data, by default None.

        Raises
        ------
        IndexError
            If `weight_names` is provided and has a different length than `indicator_names`.
        """
        super().__init__(name)
        if isinstance(annual_name, str) is False:
            raise TypeError('annual_name must be str')
        if isinstance(indicator_names, list) is False:
            raise TypeError('indicator_names must be a list')
        if all(isinstance(x, str) for x in indicator_names) is False:
            raise TypeError('indicator_names must containt str')
        if weight_names and len(weight_names) != len(indicator_names):
            raise IndexError('weight_names must have same length as indicator_names')
        self._annual_name = annual_name
        self._indicator_names = indicator_names
        self._weight_names = weight_names
        self._correction_name = correction_name
        if aggregation.lower() in ['sum', 'avg'] is False:
            raise NameError('aggregation must be sum or avg')
        self._aggregation = aggregation.lower()
        self._calls_on = {}

    @property
    def what(self):
        correction = f'{self._correction_name}*' if self._correction_name else ''
        if self._weight_names:
            aggregated_indicators = (
                '+'.join(['*'.join([x.lower(), y.lower()]) for x, y in
                          zip(self._weight_names, self._indicator_names)])
            )
        else:
            aggregated_indicators = (
                '+'.join([x.lower() for x in self._indicator_names])
            )

        numerator = f'{correction}({aggregated_indicators})'
        denominator = f'{self._aggregation}({numerator}<date {self.baseyear}>)'
        fraction = f'{numerator}/{denominator}'

        return (
            f'{self._annual_name.lower()}*<date {self.baseyear}>*{fraction}'
        )

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        """
        Evaluate the data using the provided DataFrames and return the evaluated series.

        Parameters
        ----------
        annual_df : pd.DataFrame
            The DataFrame containing annual data.
        indicator_df : pd.DataFrame
            The DataFrame containing indicator data.
        weight_df : pd.DataFrame, optional
            The DataFrame containing weight data. Defaults to None.
        correction_df : pd.DataFrame, optional
            The DataFrame containing correction data. Defaults to None.

        Raises
        ------
        ValueError
            If the baseyear is not set.
        TypeError
            If any of the input DataFrames is not of type pd.DataFrame.
        AttributeError
            If the index of any DataFrame is not of type pd.PeriodIndex or has incorrect frequency.
        IndexError
            If the baseyear is out of range for any of the DataFrames.
        NameError
            If the required column names are not present in the DataFrames.

        Returns
        -------
        pd.Series
            The evaluated series.
        """
        super().evaluate(annual_df,
                         indicator_df,
                         weight_df,
                         correction_df)

        if (self._annual_name in annual_df.columns) is False:
            raise NameError(f'Cannot find {self._annual_name} in annual_df')

        if all(x in indicator_df.columns for x in self._indicator_names) is False:
            missing = [x for x in self._indicator_names if x not in indicator_df.columns]
            raise NameError(f'Cannot find {",".join(missing)} in indicator_df')

        if self._weight_names:
            if weight_df is None:
                raise NameError(f'{self.name} expects weight_df')
            if all(x in weight_df.columns for x in self._weight_names) is False:
                missing = [x for x in self._weight_names if x not in weight_df.columns]
                raise NameError(f'Cannot find {",".join(missing)} in weight_df')

            indicator_matrix = indicator_df[self._indicator_names].to_numpy()
            weight_vector = (
                weight_df[weight_df.index.year == self.baseyear][self._weight_names]
                .to_numpy()
            )

            weighted_indicators = pd.Series(
                indicator_matrix.dot(weight_vector.transpose())[:, 0],
                index=indicator_df.index
            )
        else:
            weighted_indicators = indicator_df[self._indicator_names].sum(axis=1, skipna=False)

        if self._correction_name:
            if correction_df is None:
                raise NameError(f'{self.name} expects correction_df')
            if (self._correction_name in correction_df.columns) is False:
                raise NameError(f'{self._correction_name} is not in correction_df')
            corrected_indicators = weighted_indicators*correction_df[self._correction_name]
        else:
            corrected_indicators = weighted_indicators

        evaluated_series = (
            annual_df[annual_df.index.year == self.baseyear][self._annual_name].to_numpy()
            * corrected_indicators.div(
                    corrected_indicators[
                        corrected_indicators.index.year == self.baseyear
                    ].sum()
                    if self._aggregation == 'sum' else
                    corrected_indicators[
                        corrected_indicators.index.year == self.baseyear
                    ].mean()
                )
            )

        return evaluated_series


class FDeflate(Formula):
    def __init__(self,
                 name: str,
                 formula: Formula,
                 indicator_names: list[str],
                 weight_names: list[str] = None,
                 correction_name: str = None):
        """
        Initialize an FDeflate object.

        Parameters
        ----------
        name : str
            The name of the FDeflate formula.
        formula : Formula
            The base formula to be used.
        indicator_names : list[str]
            List of indicator names used in the formula.
        weight_names : list[str], optional
            List of weight names corresponding to the indicator names. Defaults to None.
        correction_name : str, optional
            The name of the correction factor. Defaults to None.

        Raises
        ------
        TypeError
            If `formula` is not of type Formula.
        IndexError
            If `weight_names` is provided and has a different length than `indicator_names`.
        """
        super().__init__(name)
        if isinstance(formula, Formula) is False:
            raise TypeError('formula must be of type Formula')
        if weight_names and len(weight_names) != len(indicator_names):
            raise IndexError('weight_names must have same length as indicator_names')
        self._formula = formula
        self._indicator_names = indicator_names
        self._weight_names = weight_names
        self._correction_name = correction_name
        self._calls_on = {formula.name: formula}

    @property
    def what(self):
        correction = f'{self._correction_name}*' if self._correction_name else ''
        if self._weight_names:
            aggregated_indicators = (
                '+'.join(['*'.join([x.lower(), y.lower()]) for x, y in
                          zip(self._weight_names, self._indicator_names)])
            )
        else:
            aggregated_indicators = (
                '+'.join([x.lower() for x in self._indicator_names])
            )

        numerator = f'{correction}{self._formula.name}/({aggregated_indicators})'
        denominator = f'sum({numerator}<date {self.baseyear}>)'
        fraction = f'({numerator})/{denominator}'

        return (
            f'sum({self._formula.name}<date {self.baseyear}>)*{fraction}'
        )

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        all_dfs = (annual_df, indicator_df, weight_df, correction_df)
        super().evaluate(*all_dfs)

        if all(x in indicator_df.columns for x in self._indicator_names) is False:
            raise NameError(f'All of {",".join(self._indicator_names)} is not in indicator_df')

        if self._weight_names:
            if weight_df is None:
                raise NameError(f'{self.name} expects weight_df')
            if all(x in weight_df.columns for x in self._weight_names) is False:
                raise NameError(f'All of {",".join(self._weight_names)} is not in weight_df')

            indicator_matrix = indicator_df[self._indicator_names].to_numpy()
            weight_vector = (
                weight_df[weight_df.index.year == self.baseyear][self._weight_names]
                .to_numpy()
            )

            aggregatet_indicators = pd.Series(
                indicator_matrix.dot(weight_vector.transpose())[:, 0],
                index=indicator_df.index
            )
        else:
            aggregatet_indicators = indicator_df[self._indicator_names].sum(axis=1, skipna=False)

        evaluated_formula = self._formula.evaluate(*all_dfs)

        formula_divided = evaluated_formula.div(aggregatet_indicators)

        if self._correction_name:
            if correction_df is None:
                raise NameError(f'{self.name} expects correction_df')
            if (self._correction_name in correction_df.columns) is False:
                raise NameError(f'{self._correction_name} is not in correction_df')
            formula_corrected = formula_divided*correction_df[self._correction_name]
        else:
            formula_corrected = formula_divided

        evaluated_series = (
            evaluated_formula[evaluated_formula.index.year == self.baseyear].sum()
            * formula_corrected.div(
                formula_corrected[
                    formula_corrected.index.year == self.baseyear
                ].sum()
            )
        )

        return evaluated_series


class FInflate(Formula):
    def __init__(self,
                 name: str,
                 formula: Formula,
                 indicator_names: list[str],
                 weight_names: list[str] = None,
                 correction_name: str = None):
        """
        Initialize an FInflate object.

        Parameters
        ----------
        name : str
            The name of the FDeflate formula.
        formula : Formula
            The base formula to be used.
        indicator_names : list[str]
            List of indicator names used in the formula.
        weight_names : list[str], optional
            List of weight names corresponding to the indicator names. Defaults to None.
        correction_name : str, optional
            The name of the correction factor. Defaults to None.

        Raises
        ------
        TypeError
            If `formula` is not of type Formula.
        IndexError
            If `weight_names` is provided and has a different length than `indicator_names`.
        """
        super().__init__(name)
        if isinstance(formula, Formula) is False:
            raise TypeError('formula must be of type Formula')
        if weight_names and len(weight_names) != len(indicator_names):
            raise IndexError('weight_names must have same length as indicator_names')
        self._formula = formula
        self._indicator_names = indicator_names
        self._weight_names = weight_names
        self._correction_name = correction_name
        self._calls_on = {formula.name: formula}

    @property
    def what(self):
        correction = f'{self._correction_name}*' if self._correction_name else ''
        if self._weight_names:
            aggregated_indicators = (
                '+'.join(['*'.join([x.lower(), y.lower()]) for x, y in
                          zip(self._weight_names, self._indicator_names)])
            )
        else:
            aggregated_indicators = (
                '+'.join([x.lower() for x in self._indicator_names])
            )

        numerator = f'{correction}{self._formula.name}*({aggregated_indicators})'
        denominator = f'sum({numerator}<date {self.baseyear}>)'
        fraction = f'({numerator})/{denominator}'

        return (
            f'sum({self._formula.name}<date {self.baseyear}>)*{fraction}'
        )

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        all_dfs = (annual_df, indicator_df, weight_df, correction_df)
        super().evaluate(*all_dfs)

        if all(x in indicator_df.columns for x in self._indicator_names) is False:
            raise NameError(f'All of {",".join(self._indicator_names)} is not in indicator_df')

        if self._weight_names:
            if weight_df is None:
                raise NameError(f'{self.name} expects weight_df')
            if all(x in weight_df.columns for x in self._weight_names) is False:
                raise NameError(f'All of {",".join(self._weight_names)} is not in weight_df')

            indicator_matrix = indicator_df[self._indicator_names].to_numpy()
            weight_vector = (
                weight_df[weight_df.index.year == self.baseyear][self._weight_names]
                .to_numpy()
            )

            aggregatet_indicators = pd.Series(
                indicator_matrix.dot(weight_vector.transpose())[:, 0],
                index=indicator_df.index
            )
        else:
            aggregatet_indicators = indicator_df[self._indicator_names].sum(axis=1, skipna=False)

        evaluated_formula = self._formula.evaluate(*all_dfs)

        formula_divided = evaluated_formula*aggregatet_indicators

        if self._correction_name:
            if correction_df is None:
                raise NameError(f'{self.name} expects correction_df')
            if (self._correction_name in correction_df.columns) is False:
                raise NameError(f'{self._correction_name} is not in correction_df')
            formula_corrected = formula_divided*correction_df[self._correction_name]
        else:
            formula_corrected = formula_divided

        evaluated_series = (
            evaluated_formula[evaluated_formula.index.year == self.baseyear].sum()
            * formula_corrected.div(
                formula_corrected[
                    formula_corrected.index.year == self.baseyear
                ].sum()
            )
        )

        return evaluated_series


class FSum(Formula):
    def __init__(self,
                 name,
                 *formulae: Formula):
        """
        Initialize an FSum object.

        Parameters
        ----------
        name : str
            The name of the FSum object.
        *formulae : Formula
            Variable number of Formula objects.

        Raises
        ------
        TypeError
            If any of the *formulae is not of type Formula.
        """
        super().__init__(name)
        if all(isinstance(x, Formula) for x in formulae) is False:
            raise TypeError('*formulae must be of type Formula')
        self._formulae = formulae
        self._calls_on = {x.name: x for x in formulae}

    @property
    def what(self):
        return '+'.join([x.name for x in self._formulae])

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        """
        Evaluate the data using the provided DataFrames and return the evaluated series.

        Parameters
        ----------
        annual_df : pd.DataFrame
            The DataFrame containing annual data.
        indicator_df : pd.DataFrame
            The DataFrame containing indicator data.
        weight_df : pd.DataFrame, optional
            The DataFrame containing weight data. Defaults to None.
        correction_df : pd.DataFrame, optional
            The DataFrame containing correction data. Defaults to None.

        Raises
        ------
        ValueError
            If any of the formulae do not evaluate.
        TypeError
            If any of the input DataFrames is not of type pd.DataFrame.
        AttributeError
            If the index of any DataFrame is not of type pd.PeriodIndex or has incorrect frequency.
        IndexError
            If the baseyear is out of range for any of the DataFrames.
        NameError
            If the required column names are not present in the DataFrames.

        Returns
        -------
        pd.Series
            The evaluated series.
        """
        all_dfs = (annual_df, indicator_df, weight_df, correction_df)
        super().evaluate(*all_dfs)

        if any(x.evaluate(*all_dfs) is None for x in self._formulae):
            raise ValueError('some of the formulae do not evaluate')

        return sum(
            x.evaluate(*all_dfs)
            for x in self._formulae
        )


class FSumProd(Formula):
    def __init__(self,
                 name,
                 formulae: list[Formula],
                 coefficients: list[float]):
        """
        Initialize an FSumProd object.

        Parameters
        ----------
        name : str
            The name of the FSum object.
        formulae : list[Formula]
            ...
        coefficients : list[float]
            ...

        Raises
        ------
        TypeError
            If any of the *formulae is not of type Formula.
        """
        super().__init__(name)
        if all(isinstance(x, Formula) for x in formulae) is False:
            raise TypeError('*formulae must be of type Formula')
        self._formulae = formulae
        self._coefficients = coefficients
        self._calls_on = {x.name: x for x in formulae}

    @property
    def what(self):
        return '+'.join(['*'.join([x.name, str(y)]) for x, y in
                         zip(self._formulae, self._coefficients)])
    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        """
        Evaluate the data using the provided DataFrames and return the evaluated series.

        Parameters
        ----------
        annual_df : pd.DataFrame
            The DataFrame containing annual data.
        indicator_df : pd.DataFrame
            The DataFrame containing indicator data.
        weight_df : pd.DataFrame, optional
            The DataFrame containing weight data. Defaults to None.
        correction_df : pd.DataFrame, optional
            The DataFrame containing correction data. Defaults to None.

        Raises
        ------
        ValueError
            If any of the formulae do not evaluate.
        TypeError
            If any of the input DataFrames is not of type pd.DataFrame.
        AttributeError
            If the index of any DataFrame is not of type pd.PeriodIndex or has incorrect frequency.
        IndexError
            If the baseyear is out of range for any of the DataFrames.
        NameError
            If the required column names are not present in the DataFrames.

        Returns
        -------
        pd.Series
            The evaluated series.
        """
        all_dfs = (annual_df, indicator_df, weight_df, correction_df)
        super().evaluate(*all_dfs)

        if any(x.evaluate(*all_dfs) is None for x in self._formulae):
            raise ValueError('some of the formulae do not evaluate')

        return sum(
            x.evaluate(*all_dfs)*y
            for x, y in zip(self._formulae, self._coefficients)
        )


class FMult(Formula):
    def __init__(self,
                 name,
                 formula1: Formula,
                 formula2: Formula):
        super().__init__(name)
        if isinstance(formula1, Formula) and isinstance(formula1, Formula) is False:
            raise TypeError('formula1 and formula2 must be of type Formula')
        self._formula1 = formula1
        self._formula2 = formula2
        self._calls_on = {formula1.name: formula1, formula2.name: formula2}

    @property
    def what(self):
        return f'{self._formula1.name}*{self._formula2.name}'

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        """
        Evaluate the data using the provided DataFrames and return the evaluated series.

        Parameters
        ----------
        annual_df : pd.DataFrame
            The DataFrame containing annual data.
        indicator_df : pd.DataFrame
            The DataFrame containing indicator data.
        weight_df : pd.DataFrame, optional
            The DataFrame containing weight data. Defaults to None.
        correction_df : pd.DataFrame, optional
            The DataFrame containing correction data. Defaults to None.

        Raises
        ------
        ValueError
            If the baseyear is not set.
            If formula1 does not evaluate.
            If formula2 does not evaluate.
        TypeError
            If any of the input DataFrames is not of type pd.DataFrame.
        AttributeError
            If the index of any DataFrame is not of type pd.PeriodIndex or has incorrect frequency.
        IndexError
            If the baseyear is out of range for any of the DataFrames.

        Returns
        -------
        pd.Series
            The evaluated series.
        """
        all_dfs = (annual_df, indicator_df, weight_df, correction_df)
        super().evaluate(*all_dfs)

        if self._formula1.evaluate(*all_dfs) is None:
            raise ValueError(f'formula1 does not evaluate')
        if self._formula2.evaluate(*all_dfs) is None:
            raise ValueError(f'formula2 does not evaluate')

        return (
            self._formula1.evaluate(annual_df, indicator_df, weight_df, correction_df)
            * self._formula2.evaluate(annual_df, indicator_df, weight_df, correction_df)
            )


class FDiv(Formula):
    def __init__(self,
                 name,
                 formula1: Formula,
                 formula2: Formula):
        super().__init__(name)
        if isinstance(formula1, Formula) and isinstance(formula1, Formula) is False:
            raise TypeError('formula1 and formula2 must be of type Formula')
        self._formula1 = formula1
        self._formula2 = formula2
        self._calls_on = {formula1.name: formula1, formula2.name: formula2}

    @property
    def what(self):
        return f'{self._formula1.name}/{self._formula2.name}'

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        """
        Evaluate the data using the provided DataFrames and return the evaluated series.

        Parameters
        ----------
        annual_df : pd.DataFrame
            The DataFrame containing annual data.
        indicator_df : pd.DataFrame
            The DataFrame containing indicator data.
        weight_df : pd.DataFrame, optional
            The DataFrame containing weight data. Defaults to None.
        correction_df : pd.DataFrame, optional
            The DataFrame containing correction data. Defaults to None.

        Raises
        ------
        ValueError
            If the baseyear is not set.
            If formula1 does not evaluate.
            If formula2 does not evaluate.
        TypeError
            If any of the input DataFrames is not of type pd.DataFrame.
        AttributeError
            If the index of any DataFrame is not of type pd.PeriodIndex or has incorrect frequency.
        IndexError
            If the baseyear is out of range for any of the DataFrames.

        Returns
        -------
        pd.Series
            The evaluated series.
        """
        all_dfs = (annual_df, indicator_df, weight_df, correction_df)
        super().evaluate(*all_dfs)

        if self._formula1.evaluate(*all_dfs) is None:
            raise ValueError(f'formula1 does not evaluate')
        if self._formula2.evaluate(*all_dfs) is None:
            raise ValueError(f'formula2 does not evaluate')

        return (
            self._formula1.evaluate(annual_df, indicator_df, weight_df, correction_df)
            .div(self._formula2.evaluate(annual_df, indicator_df, weight_df, correction_df))
            )


class MultCorr(Formula):
    def __init__(self, formula: Formula, correction_name):
        """
        Initialize a MultCorr object.

        Parameters
        ----------
        formula : Formula
            The Formula object to be multiplied by the correction factor.
        correction_name : str
            The name of the correction factor.

        Raises
        ------
        TypeError
            If formula is not of type Formula.
        """
        super().__init__(formula.name)
        if isinstance(formula, Formula) is False:
            raise TypeError('formula must be of type Formula')
        self._formula = formula
        self._correction_name = correction_name
        self._calls_on = formula._calls_on

    @property
    def what(self):
        return (
            f'sum(({self._formula.what})<date {self.baseyear}>)*'
            f'{self._correction_name}*({self._formula.what})/'
            f'sum({self._correction_name}*({self._formula.what})<date {self.baseyear}>)'
        )

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        """
        Evaluate the data using the provided DataFrames and return the evaluated series.

        Parameters
        ----------
        annual_df : pd.DataFrame
            The DataFrame containing annual data.
        indicator_df : pd.DataFrame
            The DataFrame containing indicator data.
        weight_df : pd.DataFrame, optional
            The DataFrame containing weight data. Defaults to None.
        correction_df : pd.DataFrame, optional
            The DataFrame containing correction data. Defaults to None.

        Raises
        ------
        ValueError
            If the baseyear is not set.
        TypeError
            If any of the input DataFrames is not of type pd.DataFrame.
        AttributeError
            If the index of any DataFrame is not of type pd.PeriodIndex or has incorrect frequency.
        IndexError
            If the baseyear is out of range for any of the DataFrames.
        NameError
            If the required column names are not present in the DataFrames.

        Returns
        -------
        pd.Series
            The evaluated series.
        """
        all_dfs = (annual_df, indicator_df, weight_df, correction_df)
        super().evaluate(*all_dfs)

        evaluated_formula = self._formula.evaluate(*all_dfs)

        formula_corrected = evaluated_formula*correction_df[self._correction_name]

        return (
            evaluated_formula[evaluated_formula.index.year == self.baseyear].sum()*
            formula_corrected.div(
                formula_corrected[formula_corrected.index.year == self.baseyear].sum()
            )
        )


class AddCorr(Formula):
    def __init__(self, formula: Formula, correction_name):
        """
        Initialize an AddCorr object.

        Parameters
        ----------
        formula : Formula
            The Formula object to be added with the correction factor.
        correction_name : str
            The name of the correction factor.

        Raises
        ------
        TypeError
            If formula is not of type Formula.
        """
        super().__init__(formula.name)
        if isinstance(formula, Formula) is False:
            raise TypeError('formula must be of type Formula')
        self._formula = formula
        self._correction_name = correction_name
        self._calls_on = formula.calls_on

    @property
    def what(self):
        return f'{self._correction_name}+({self._formula.what})-avg({self._correction_name}<date {self.baseyear})'

    def evaluate(self,
                 annual_df: pd.DataFrame,
                 indicator_df: pd.DataFrame,
                 weight_df: pd.DataFrame = None,
                 correction_df: pd.DataFrame = None) -> pd.Series:
        """
        Evaluate the data using the provided DataFrames and return the evaluated series.

        Parameters
        ----------
        annual_df : pd.DataFrame
            The DataFrame containing annual data.
        indicator_df : pd.DataFrame
            The DataFrame containing indicator data.
        weight_df : pd.DataFrame, optional
            The DataFrame containing weight data. Defaults to None.
        correction_df : pd.DataFrame, optional
            The DataFrame containing correction data. Defaults to None.

        Raises
        ------
        ValueError
            If the baseyear is not set.
        TypeError
            If any of the input DataFrames is not of type pd.DataFrame.
        AttributeError
            If the index of any DataFrame is not of type pd.PeriodIndex or has incorrect frequency.
        IndexError
            If the baseyear is out of range for any of the DataFrames.
        NameError
            If the required column names are not present in the DataFrames.

        Returns
        -------
        pd.Series
            The evaluated series.
        """
        all_dfs = (annual_df, indicator_df, weight_df, correction_df)
        super().evaluate(*all_dfs)

        return (
            correction_df[self._correction_name]
            + self._formula.evaluate(*all_dfs)
            - correction_df[correction_df.index.year == self.baseyear][self._correction_name].mean()
        )