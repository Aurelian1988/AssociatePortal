import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from profile_document_ocr import extract_fields
class ExtractionTests(unittest.TestCase):
    def test_labelled_passport(self):
        result=extract_fields('Passport number: 123456789\nDate of birth: 01 Jan 1990\nDate of issue: 02 Feb 2020\nDate of expiry: 02 Feb 2030\nNationality: BRITISH CITIZEN\nPlace of birth: LONDON','passport')
        self.assertEqual(result['dob'],'1990-01-01')
        self.assertEqual(result['passport_issue_date'],'2020-02-02')
        self.assertNotIn('birth_country',result)
        self.assertNotIn('birth_nationality',result)
        self.assertEqual(result['_passport_nationality'],'BRITISH CITIZEN')
    def test_unlabelled_dates_not_guessed(self):
        self.assertEqual(extract_fields('01 Jan 1990\n02 Feb 2020\n02 Feb 2030','passport'),{})
    def test_licence_dates_distinct(self):
        result=extract_fields('4a. 01.01.2020\n4b. 01.01.2030\nUNITED KINGDOM','licence_front')
        self.assertEqual(result['dl_issue_date'],'2020-01-01')
        self.assertEqual(result['dl_photocard_expiry'],'2030-01-01')
        self.assertNotIn('dl_expiry_date',result)
    def test_checked_mrz_and_corrupt_read(self):
        from profile_document_ocr import check_digit, mrz_passport
        first='P<GBRTEST<<ALICE<MARIA'.ljust(44,'<')
        self.assertEqual(len(first),44)
        number='123456789';dob='900101';expiry='300101';optional='<'*14
        second=number+check_digit(number)+'GBR'+dob+check_digit(dob)+'F'+expiry+check_digit(expiry)+optional+'0'
        second+=check_digit(second[:10]+second[13:20]+second[21:43])
        result=mrz_passport(first+'\n'+second)
        self.assertEqual(result['first_name'],'Alice')
        self.assertEqual(result['middle_name'],'Maria')
        self.assertEqual(result['dob'],'1990-01-01')
        self.assertEqual(result['passport_expiry_date'],'2030-01-01')
        self.assertEqual(mrz_passport(first+'\n'+'9'+second[1:]),{})
        # Newer passports can use PP, not just P<, for their document type.
        self.assertEqual(mrz_passport('PP'+first[2:]+'\n'+second)['passport_number'],number)
        # Check digits cover the second line, not the names: reject digit noise
        # in the name line instead of presenting it as a person's name.
        self.assertEqual(mrz_passport(first[:-1]+'3\n'+second),{})

    def test_bilingual_issue_label_and_spaced_numeric_date(self):
        result=extract_fields('Date de délivrance / Date of issue\n04 06 2020','passport')
        self.assertEqual(result['passport_issue_date'],'2020-06-04')

    def test_licence_ocr_noise_and_adjacent_authority(self):
        result=extract_fields('noise 4a. 12.03.2021 4c. DVLA\n4b. 12.03.2031 stray\nnoise 5 TESTE901015AB9CD 02','licence_front')
        self.assertEqual(result['dl_issue_date'],'2021-03-12')
        self.assertEqual(result['dl_photocard_expiry'],'2031-03-12')
        self.assertEqual(result['dl_number'],'TESTE901015AB9CD')
        self.assertEqual(result['dl_issuing_country'],'United Kingdom')

    def test_does_not_copy_expiry_into_unread_issue_date(self):
        result=extract_fields('4a. unreadable\n4b. 12.03.2031','licence_front')
        self.assertNotIn('dl_issue_date',result)
        self.assertEqual(result['dl_photocard_expiry'],'2031-03-12')

    def test_birthplace_does_not_set_issuing_country(self):
        self.assertNotIn('dl_issuing_country',extract_fields('3. 01.01.1990 UNITED KINGDOM','licence_front'))

    def test_bilingual_short_year_requires_context_and_matching_months(self):
        context={'passport_expiry_date':'2030-02-03'}
        result=extract_fields('Date of issue / Date de délivrance (7)\n03 FEB / FEV 20','passport',context=context)
        self.assertEqual(result['passport_issue_date'],'2020-02-03')
        self.assertNotIn('passport_issue_date',extract_fields('Date of issue\n03 FEB / FEV 20','passport'))
        self.assertNotIn('passport_issue_date',extract_fields('Date of issue\n03 FEB / DEC 20','passport',context=context))
        self.assertNotIn('passport_issue_date',extract_fields('Date of issue\n31 FEB / FEV 20','passport',context=context))

    def test_small_bilingual_label_still_requires_issue_phrase(self):
        result=extract_fields('Dale de délivrance (7)\n03 FEB / FEV 20','passport',context={'passport_expiry_date':'2030-02-03'})
        self.assertEqual(result['passport_issue_date'],'2020-02-03')
        self.assertNotIn('passport_issue_date',extract_fields('03 FEB / FEV 20','passport',context={'passport_expiry_date':'2030-02-03'}))

    def test_licence_identity_requires_printed_labels(self):
        result=extract_fields('1. SMITH\n2. ALEX MARIA\n3. 15.08.1987 UNITED KINGDOM\n4c. DVLA','licence_front')
        self.assertEqual(result['last_name'],'Smith');self.assertEqual(result['first_name'],'Alex')
        self.assertEqual(result['middle_name'],'Maria');self.assertEqual(result['dob'],'1987-08-15')
        self.assertNotIn('first_name',extract_fields('ALEX SMITH\n15.08.1987','licence_front'))
