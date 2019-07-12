from bs4 import BeautifulSoup

import bs4
import requests
import logging
import json


class BCAPI:

    base_url = "http://buscacursos.uc.cl/"

    key_map = {
        'NRC': "nrc",
        'Sigla': "initials",
        'Permite Retiro': "allows_withdrawal",
        '¿Se dicta en inglés?': "english",
        'Sec.': "section",
        '¿Requiere Aprob. Especial?': "special_approval",
        'Categoría': "category",
        'Nombre': "name",
        'Profesor': "professor",
        'Campus': "campus",
        'Créd.': "credits",
        'Vacantes Totales': "total_vacancies",
        'Vacantes Disponibles': "free_vacancies",
        'Vacantes Reservadas': "reserved_vacancies",
        'Horario': "schedule",
        'Escuela': "school"
    }

    @classmethod
    def semester_options(cls):
        soup = BeautifulSoup(requests.get(cls.base_url).text, "lxml")
        return {op.text: op.attrs["value"] for op in soup.findAll("select", attrs={"name": "cxml_semestre"})[0].findChildren()}

    @classmethod
    def category_options(cls):
        soup = BeautifulSoup(requests.get(cls.base_url).text, "lxml")
        return {op.text: op.attrs["value"] for op in soup.findAll("select", attrs={"name": "cxml_categoria"})[0].findChildren()}

    @classmethod
    def campus_options(cls):
        soup = BeautifulSoup(requests.get(cls.base_url).text, "lxml")
        return {op.text: op.attrs["value"] for op in soup.findAll("select", attrs={"name": "cxml_campus"})[0].findChildren()}

    @classmethod
    def academic_unit_options(cls):
        soup = BeautifulSoup(requests.get(cls.base_url).text, "lxml")
        return {op.text: op.attrs["value"] for op in soup.findAll("select", attrs={"name": "cxml_unidad_academica"})[0].findChildren()}

    @classmethod
    def search_html(cls, semester, initials="", nrc="", name="", professor="", category="TODOS", campus="TODOS", academic_unit="TODOS"):
        return requests.get(cls.base_url, params={
            "cxml_semestre": semester,
            "cxml_sigla": initials,
            "cxml_nrc": nrc,
            "cxml_nombre": name,
            "cxml_categoria": category,
            "cxml_profesor": professor,
            "cxml_campus": campus,
            "cxml_unidad_academica": academic_unit
        }).text

    @classmethod
    def search_json(cls, semester, initials="", nrc="", name="", professor="", category="TODOS", campus="TODOS", academic_unit="TODOS"):
        html = cls.search_html(semester, initials, nrc,
                               name, professor, category, campus, academic_unit)
        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")

        try:
            trs = tables[5].findChildren("tr", recursive=False)
        except IndexError:
            logging.warning("No courses were found")
            return "[]", False

        courses = []
        escuela = ""
        headers = trs[1].text.strip().split("\n")[:11] + ["Vacantes Totales", "Vacantes Disponibles",
                                                          "Vacantes Reservadas"] + trs[1].text.strip().split("\n")[12:]
        for row in trs:
            if len(row.findChildren("td", recursive=False)) == 1:
                escuela = row.td.text
            elif len(row.findChildren("td", recursive=False)) == 16:
                course = dict(
                    zip(headers, [r.text.strip() for r in row.findChildren("td", recursive=False)]))
                course["Escuela"] = escuela
                courses.append(course)
        courses = cls._parse_attributes(courses)
        return json.dumps(courses, ensure_ascii=False), bool(soup.findAll("div", class_="bordeBonito"))

    @classmethod
    def _parse_attributes(cls, courses):
        for course in courses:
            course["Profesor"] = [{"first_name": p.strip().split(" ")[1], "last_name": p.strip(
            ).split(" ")[0]} for p in course["Profesor"].split(",")]
            course.pop("Agregar al horario", None)
            items = list(course.items())
            for key, val in items:
                if isinstance(val, str) and val.isnumeric():
                    course[key] = int(val)
                elif val == "SI":
                    course[key] = True
                elif val == "NO":
                    course[key] = False
                elif val == "":
                    course[key] = None
                elif key == "Horario":
                    course[key] = cls.__parse_schedule(val)
                course[cls.key_map[key]] = course.pop(key)

        return courses

    @classmethod
    def __parse_schedule(cls, sched_str):
        def parse(e):
            e = e.split("\n\n\n")
            days, block = e[0].split(":")
            days = days.split("-")
            block = block.split(",")
            return {"classroom": e[2], "type": e[1], "blocks": {"days": days, "block": block}}
        return [parse(e) for e in sched_str.split("\n\n\n\n\n")]
