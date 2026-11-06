"""Canonical user-entered names and the contact display name."""
import re
import unicodedata

NAME_FIELDS={'first_name','middle_name','last_name','mothers_first_name','mothers_maiden_name'}

def normalise_name(value):
    value=unicodedata.normalize('NFC',str(value or ''))
    value=''.join(' ' if unicodedata.category(c)=='Pd' else c for c in value)
    return re.sub(r'\s+',' ',value).strip().title()

def valid_name(value):
    return all(c.isspace() or c.isalpha() or unicodedata.category(c).startswith('M') for c in str(value or ''))

def contact_name(values):
    return ' '.join(normalise_name(values.get(key)) for key in ('first_name','middle_name','last_name') if normalise_name(values.get(key)))


def unique_contact_name(doc):
    """Disambiguate the display name only; never alter personal name fields."""
    import frappe
    base = contact_name(doc)
    duplicate = frappe.db.exists('Associate', {
        'contact_name': base, 'name': ['!=', doc.name],
    })
    return f'{base} {doc.name}' if duplicate else base
