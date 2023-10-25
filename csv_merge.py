import polars as pl

# create master sheet for use in program
zip_cbsa_092023_df = pl.read_excel("./augmenting_data/ZIP_CBSA_092023.xlsx")
cbsa_est_df = pl.read_csv("./augmenting_data/cbsa-est2022.csv")

zip_cbsa_df = zip_cbsa_092023_df.select(
    ["ZIP", "CBSA", "USPS_ZIP_PREF_CITY", "USPS_ZIP_PREF_STATE"]
)
cbsa_cbsa_title_df = cbsa_est_df.select(["CBSA", "NAME", "LSAD"])

master_df = zip_cbsa_df.join(cbsa_cbsa_title_df, on="CBSA", how="inner")

master_df = master_df.rename(
    {
        "USPS_ZIP_PREF_CITY": "CITY",
        "USPS_ZIP_PREF_STATE": "STATE_ID",
        "NAME": "METRO_NAME",
    }
)

master_df.write_csv("./augmenting_data/master.csv")
