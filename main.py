import numpy as np
import pandas as pd
import matplotlib.pyplot as plt 
import os
import seaborn as sns
from sklearn.preprocessing import OneHotEncoder
from pipeline_functions import *
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
import optuna
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import ipdb

path = os.path.join("data","PastLoans.csv")
path_new_set = os.path.join("data","NewApplications_3_Round1.csv")

if __name__ == "__main__":
    df = pd.read_csv(path, index_col='id')
    X = df.iloc[:,:-1]
    y = df.iloc[:,-1]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=42)
    pipeline = full_pipeline()
    X_train_final = pipeline.fit_transform(X_train)
    X_val_final = pipeline.transform(X_val)
    X_test_final = pipeline.transform(X_test)
    optuna_objective = create_complete_pipeline(X_train_final, y_train, X_val_final, y_val)
    study = optuna.create_study(direction="maximize")
    study.optimize(optuna_objective, n_trials=40, n_jobs=-1)
    print("Number of finished trials: ", len(study.trials))
    print("Best trial:")
    trial = study.best_trial
    print("  Value: {}".format(trial.value))
    params_xgb={}
    params_lgbm={} 
    params_weights = {}
    print("  Params: ")
    for key, value in trial.params.items():
        print("    {}: {}".format(key, value))
        if key in liste_lgbm:
            params_lgbm[key]=value
        if key in liste_xgb:
            params_xgb[key]=value
        else:
            params_weights[key]=value

    model_lgbm = LGBMClassifier(**params_lgbm)
    model_xgb = XGBClassifier(**params_xgb)
    sample_weights = compute_sample_weight(class_weight="balanced",y = y_train)
    model_xgb.fit(X_train_final,y_train, sample_weight=sample_weights)
    model_lgbm.fit(X_train_final,y_train, sample_weight=sample_weights)
    # preds = model.predict_proba(X_test_final)
    # preds_class = model.predict(X_test_final)
    preds_lgbm = model_lgbm.predict_proba(X_test_final)[:,1]
    preds_xgb = model_xgb.predict_proba(X_test_final)[:,1]
    # ipdb.set_trace()
    preds_class = optimal_mix_predictions(preds_lgbm,preds_xgb,**params_weights)
    matrix_confusion = confusion_matrix(y_test, preds_class)
    print(matrix_confusion)

    df_new_preds = pd.read_csv(path_new_set,index_col="id")
    X_new = df_new_preds.iloc[:,:]
    X_new_scaled = pipeline.transform(X_new)
    predictions = 0.5*(model_lgbm.predict_proba(X_new_scaled)+model_xgb.predict_proba(X_new_scaled))
    df_preds = pd.DataFrame(predictions, columns=["Proba no Default","Proba Default"])
    ipdb.set_trace()