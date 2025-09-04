from __future__ import annotations
import pandera as pa
from pandera import Column, DataFrameSchema


PriceSchema = DataFrameSchema({
"symbol": Column(str),
"open": Column(float),
"high": Column(float),
"low": Column(float),
"close": Column(float),
"volume": Column(float, nullable=True),
})


# we validate columns and rely on loader to set UTC index.