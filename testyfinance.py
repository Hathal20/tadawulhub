import yfinance as yf

# Download simple data
data = yf.download("AAPL", period="5d", interval="1d")

# Flatten: drop the second level (the ticker name)
data.columns = data.columns.droplevel(1)

print(data)
