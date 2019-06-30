# Iodide notebook demo
[Report](https://alpha.iodide.io/notebooks/2121/?viewMode=report) | [Code](https://alpha.iodide.io/notebooks/2121/) 

# todo
- поддержка вместо результата
- монте-карло гистограммы и просто кол-ва целочисленных участков
- эллипс mcd
- аномальная часть
- разница между фактическим и ожидаемым результатом по целым значениям (fig. 3) по регионам

# глоссарий

**electoral_id** - ascii строка

**region_name** - unicode строка, человекочитаемое нормализованное название региона

**region_code** - ascii строка, короткий код региона (в редких случаях административной единицы). предполагается, что эти коды из ISO_3166-2, возможно, с небольшими расширениями

**territory** - unicode строка

**election_name** - unicode строка

**voters_registered** - int, количество избирателей в списке. Точнее: "число избирателей, внесенных в список избирателей на момент окончания голосования"

**voters_voted_at_station** - int, количество бюллетеней, выданных на участке. Точнее: "число бюллетеней, выданных в помещении в день голосования"

**voters_voted_outside_station** - int, количество бюллетеней, выданных вне участка. Точнее: "число бюллетеней, выданных вне помещения в день голосования"

**voters_voted_early** - int, количество бюллетеней, выданных досрочно. Точнее: "число бюллетеней, выданных досрочно"

**ballots_valid** - int, количество действительных бюллетеней. Точнее: "число действительных бюллетеней"

**ballots_invalid** - int, количество недейтсвительных бюллетеней. Точнее: "число недействительных бюллетеней"

**voters_voted** - int

# links

https://github.com/zeroepoch/plotbitrate/blob/master/plotbitrate.py
https://github.com/avsmal/cikrf_crawler/blob/master/cikrf/spiders/UIKSpider.py

https://github.com/dkobak/elections (https://vk.com/avsmal?w=wall2541_14424%2Fall, https://avsmal.livejournal.com/24683.html)
https://arxiv.org/abs/1204.0307


https://habr.com/ru/post/352424/

https://cikinfo.modos189.ru

https://habr.com/en/post/354020/

https://corbulon.livejournal.com/175917.html https://corbulon.livejournal.com/177010.html

https://lleo.me/dnevnik/2017/09/11_1.html

https://habr.com/ru/post/358790/  https://2018.krutika.ru/digits?r=bashkortostan,dagestan,karachaev-cherkess,tatarstan,krasnodar,stavropol,kemerovo,saratov

#### Карты
- https://elections.dekoder.org/ukraine/ua
- http://texty.org.ua/d/2019/president_elections_v2/
- https://habr.com/ru/company/ods/blog/338554/

