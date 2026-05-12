# 1️⃣ Split a CSV (stratified for classification)
python ml_utils.py split data.csv label --test-size 0.25 --stratify --out-dir ./splits

# 2️⃣ Scale the splits (standard scaling, persist the scaler)
python ml_utils.py scale ./splits/train.csv ./splits/test.csv \
      --method standard --save-scaler ./scaler.joblib --out-dir ./scaled

# 3️⃣ Train a logistic‑regression model
python ml_utils.py train ./scaled/train_scaled.csv \
      --target label --model logistic_regression \
      --params '{"C": 1.0, "penalty": "l2"}' \
      --model-out ./model_lr.pkl

# 4️⃣ Evaluate on the held‑out test set (auto‑chooses classification metrics)
python ml_utils.py evaluate ./model_lr.pkl ./scaled/test_scaled.csv \
      --target label

# 5️⃣ Grid‑search a RandomForest classifier
python ml_utils.py search ./scaled/train_scaled.csv \
      --target label \
      --model random_forest \
      --param-grid '{"n_estimators": [100,200], "max_depth": [5,10]}' \
      --cv 3 \
      --out ./rf_grid.pkl


# imports that can be installed directly 
from ml_utils import split_dataset, scale_features, train_model, evaluate_model

df = pd.read_csv("data.csv")
X_train, X_test, y_train, y_test = split_dataset(df, target_column="label")
X_train_s, X_test_s = scale_features(X_train, X_test, method="standard")

model = train_model(X_train_s, y_train, model_type="logistic_regression")
metrics = evaluate_model(model, X_test_s, y_test)
print(metrics)

