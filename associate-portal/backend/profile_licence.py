"""ERP business classification by issuing country, not entitlement verification."""
EU_COUNTRIES = set("Austria|Belgium|Bulgaria|Croatia|Cyprus|Czechia|Czech Republic|Denmark|Estonia|Finland|France|Germany|Greece|Hungary|Ireland|Italy|Latvia|Lithuania|Luxembourg|Malta|Netherlands|Poland|Portugal|Romania|Slovakia|Slovenia|Spain|Sweden".lower().split('|'))
def licence_type(country):
    country = str(country or '').strip().casefold()
    if not country: return ''
    if country in {'united kingdom','northern ireland','uk','gb','gbr'}: return 'Full UK'
    return 'EU' if country in EU_COUNTRIES else 'International'
