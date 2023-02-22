from datetime import date

now = date.today()
now_year = now.year


def year(request):
    return {
        'year': now_year
    }
