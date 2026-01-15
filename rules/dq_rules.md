# Data Quality Rules — E‑commerce Shopper Behavior

## DQ‑01 – Missing values
Si une colonne contient plus de **20 % de valeurs manquantes** :
- 20–40 % → WARNING
- >40 % → REJECT

Colonnes particulièrement sensibles :
- user_id, age, gender, country, income_level, weekly_purchases, monthly_spend, average_order_value, last_purchase_date

Raison : données critiques pour l’analyse comportementale.

---

## DQ‑02 – Dataset vide
Si le dataset a **0 lignes**, décision = **REJECT**.

Raison : pas de données à analyser.

---

## DQ‑03 – Types de données incohérents
Vérification des types :
- user_id → entier ou string
- age → entier
- gender, country, urban_rural, income_level, employment_status, education_level, relationship_status, occupation, ethnicity, language_preference, device_type, preferred_payment_method, budgeting_style → catégories
- weekly_purchases, monthly_spend, cart_abandonment_rate, average_order_value, coupon_usage_frequency, referral_count, loyalty_program_member, impulse_purchases_per_month, browse_to_buy_ratio, return_frequency, brand_loyalty_score, impulse_buying_score, environmental_consciousness, health_conscious_shopping, travel_frequency, hobby_count, social_media_influence_score, reading_habits, exercise_frequency, stress_from_financial_decisions, overall_stress_level, sleep_quality, physical_activity_level, mental_health_score, daily_session_time_minutes, product_views_per_day, ad_views_per_day, ad_clicks_per_day, wishlist_items_count, cart_items_average, checkout_abandonments_per_month, purchase_conversion_rate, app_usage_frequency, notification_response_rate, account_age_months, return_rate → numériques
- last_purchase_date → date

Si type inattendu → **WARNING**

---

## DQ‑04 – Negative values impossibles
Pour les colonnes numériques où les valeurs négatives n’ont pas de sens :
- age, weekly_purchases, monthly_spend, average_order_value, coupon_usage_frequency, referral_count, impulse_purchases_per_month, browse_to_buy_ratio, return_frequency, social_media_influence_score, daily_session_time_minutes, product_views_per_day, ad_views_per_day, ad_clicks_per_day, wishlist_items_count, cart_items_average, checkout_abandonments_per_month, purchase_conversion_rate, account_age_months, return_rate

Si valeur < 0 → **WARNING**

---

## DQ‑05 – Outliers extrêmes
Pour colonnes numériques continues :
- monthly_spend, average_order_value, weekly_purchases, cart_abandonment_rate, impulse_purchases_per_month, daily_session_time_minutes, product_views_per_day, ad_views_per_day, ad_clicks_per_day

Détection via **IQR** :
- Outliers > 1.5 * IQR → si > 5 % des lignes → **WARNING**

---

## DQ‑06 – Dates invalides
- last_purchase_date → doit être une date valide
- >5 % d’invalides → **WARNING**

---

## DQ‑07 – Cohérence catégorielle
- loyalty_program_member, premium_subscription → valeurs attendues : Yes/No ou 0/1
- urban_rural → values attendues : Urban / Rural
- gender → Male / Female / Other

Valeurs inattendues → **WARNING**

---

## DQ‑08 – Identifiants dupliqués
- user_id et account_age_months → duplicats élevés → **WARNING**

Raison : duplication peut indiquer erreur de collecte.

---

## DQ‑09 – Cohérence des ratios
- cart_abandonment_rate, browse_to_buy_ratio, purchase_conversion_rate → doivent être entre 0 et 1

Si hors bornes → **WARNING**

---

## DQ‑10 – Cohérence comportementale
- weekly_purchases, monthly_spend, average_order_value → cohérence approximative (ex : monthly_spend ≥ weekly_purchases * average_order_value)

Violation → **WARNING**
