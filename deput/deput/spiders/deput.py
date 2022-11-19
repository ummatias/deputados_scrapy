import os

import scrapy
from scrapy.selector import Selector


class DeputSpider(scrapy.Spider):
    name = "DeputSpider"

    def parse(self, response, gender="female"):
        info = self._format_info(response.css("ul.informacoes-deputado li").getall())
        presencas = self._format_presenca(
            response.css("dl.list-table__definition-list").getall()
        )
        gastos = self._format_gastos(response.css("li.gasto").getall())
        salario_bruto = "R$ " + (
            response.css("div.beneficio h3:contains('Salário mensal bruto') + a::text")
            .get()[2:]
            .strip()
        )

        out_dict = {}
        out_dict["nome"] = info["nome_civil"]
        out_dict["genero"] = response.meta.get("gender")
        out_dict.update(presencas[0])
        out_dict.update(presencas[1])
        out_dict["data_nascimento"] = info["data_de_nascimento"]
        out_dict.update(gastos[0])
        out_dict.update(gastos[1])
        out_dict["salario_bruto"] = salario_bruto

        yield out_dict

    def start_requests(self):
        urls = self._load_urls("../../data/")
        for url in urls:
            yield scrapy.Request(
                url=url[0], callback=self.parse, meta={"gender": f"{url[1]}"}
            )

    def _load_urls(self, path):
        urls = []
        for file_path in os.listdir(path):
            with open(os.path.join(path, file_path), "r") as f:
                lines = f.readlines()
                for line in lines:
                    if file_path.split(".")[0].endswith("as"):
                        urls.append((line.strip(), "female"))
                    else:
                        urls.append((line.strip(), "male"))
        return urls

    def _format_presenca(self, dl):
        presencas = {}
        for i, d in enumerate(dl):
            presence_type = "plenario" if i == 0 else "comissao"
            aux = [dd.strip() for dd in Selector(text=d).css("dd::text").getall()]
            presencas[i] = {
                f"presença_{presence_type}": aux[0],
                f"ausencia_{presence_type}": aux[1],
                f"ausencia_justificada_{presence_type}": aux[2],
            }

        return presencas

    def _format_info(self, info_dep):
        info = {}
        for i in info_dep:
            aux = (
                Selector(text=i)
                .css("span::text")
                .get()[:-1]
                .strip()
                .lower()
                .replace(" ", "_")
            )
            info[aux] = (
                Selector(text=i).css("li::text").get().replace("\n", " ").strip()
            )
        return info

    def _format_gastos(self, gastos):
        all_gastos = {}
        for i, g in enumerate(gastos):
            trs = Selector(text=g).css("tr").getall()[1:]

            all_gastos[i] = {}
            for tr in trs:
                values = Selector(text=tr).css("td::text").getall()
                try:
                    all_gastos[i][values[0]] = values[1]
                except IndexError:
                    pass

        for key in all_gastos:
            data_type = "par" if key == 0 else "gab"
            all_gastos[key].pop("Total Disponível")
            all_gastos[key][f"gasto_total_{data_type}"] = all_gastos[key].pop(
                "Total Gasto"
            )
            for k in list(all_gastos[key].keys()):
                if len(k) == 3:
                    all_gastos[key][f"gasto_{k.lower()}_{data_type}"] = all_gastos[
                        key
                    ].pop(k)

        return all_gastos
