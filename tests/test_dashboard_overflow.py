import pyarrow as pa
from unitime_app.data_loader import load_classes

def test_classes_dates_string_conversion():
    df = load_classes()
    # all dates should be strings
    assert df['dates'].apply(lambda x: isinstance(x, str)).all()
    # Convert to Arrow table (what Streamlit does internally)
    table = pa.Table.from_pandas(df.head(20))
    assert isinstance(table, pa.Table)
