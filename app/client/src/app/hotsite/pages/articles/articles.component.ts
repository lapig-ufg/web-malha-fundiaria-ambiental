import { Component, OnInit } from '@angular/core';
import { LocalizationService } from "../../../@core/internationalization/localization.service";
import { LangChangeEvent } from "@ngx-translate/core";

import { Article } from '@core/interfaces';

@Component({
  standalone: false,
  selector: 'app-articles',
  templateUrl: './articles.component.html',
  styleUrls: ['./articles.component.scss']
})
export class ArticlesComponent implements OnInit {

  public search: string = '';
  public articles: Article[] = [];
  public lang: string;

  private allArticles = [
    {
      "doi": "https://doi.org/10.1126/science.abq7768",
      "authors": "De Marco Jr., P. et al.",
      "published": "2023-04-21",
      "image": "assets/hotsite/images/articles/the_value_of_private_properties_for_the_conservation_of_biodiversity_in_the_brazilian_cerrado.png",
      "pt": {
        "title": "O valor das propriedades privadas para a conservação da biodiversidade no Cerrado brasileiro",
        "abstract": "Áreas reservadas para conservação em terras privadas podem ser fundamentais para melhorar paisagens favoráveis à biodiversidade. Essa estratégia de conservação deve ser especialmente eficaz em regiões altamente ameaçadas que são mal protegidas por terras públicas, como o Cerrado brasileiro. Determinamos que áreas protegidas privadas acomodam até 14,5% das distribuições de espécies de vertebrados ameaçadas, o que aumenta para 25% ao considerar a distribuição do habitat nativo restante."
      },
      "en": {
        "title": "The value of private properties for the conservation of biodiversity in the Brazilian Cerrado",
        "abstract": "Areas set aside for conservation within private lands may be key to enhancing biodiversity-friendly landscapes. This conservation strategy should be especially effective in highly threatened regions that are poorly protected by public lands, such as the Brazilian Cerrado. We determined that private protected areas accommodate up to 14.5% of threatened vertebrate species ranges, which increases to 25% when considering the distribution of remaining native habitat."
      }
    },
    {
      "doi": "https://doi.org/10.1088/1748-9326/acd20a",
      "authors": "Camara, G. et al.",
      "published": "2023-05-12",
      "image": "assets/hotsite/images/articles/impact_of_land_tenure_on_deforestation_control_and_forest_restoration_in_brazilian_amazonia.png",
      "pt": {
        "title": "Impacto da posse da terra no controle do desmatamento e na restauração florestal na Amazônia brasileira",
        "abstract": "Este estudo examina como a estrutura fundiária restringe a capacidade do Brasil de cumprir suas metas de controle do desmatamento e restauração florestal no bioma Amazônia. Os resultados mostram que grande parte do desmatamento ocorre em propriedades privadas e apontam para a necessidade de combinar estratégias de comando e controle com políticas de mercado para alcançar os objetivos ambientais do país."
      },
      "en": {
        "title": "Impact of land tenure on deforestation control and forest restoration in Brazilian Amazonia",
        "abstract": "This study examines how land tenure constrains Brazil's ability to meet its deforestation control and forest restoration goals in its Amazonia biome. Findings show that a large portion of deforestation occurs on private lands, highlighting the need to combine robust command-and-control strategies with market-based policies to achieve the country's environmental targets."
      }
    },
    {
      "doi": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12651.html",
      "authors": "Presidência da República, Brasil",
      "published": "2012-05-25",
      "image": "assets/hotsite/images/articles/lei_12651_codigo_florestal.png",
      "pt": {
        "title": "Lei nº 12.651, de 25 de maio de 2012 (Código Florestal Brasileiro)",
        "abstract": "Estabelece normas gerais sobre a proteção da vegetação nativa, Áreas de Preservação Permanente (APP) e áreas de Reserva Legal. A lei dispõe sobre a exploração florestal, controle de incêndios e instrumentos econômicos para conciliar o uso produtivo da terra com a preservação ambiental."
      },
      "en": {
        "title": "Law No. 12,651, of May 25, 2012 (Brazilian Forest Code)",
        "abstract": "Establishes general rules for the protection of native vegetation, Permanent Preservation Areas (APP), and Legal Reserves. The law regulates forest exploitation, fire control, and economic instruments to reconcile productive land use with environmental preservation."
      }
    },
    {
      "doi": "https://doi.org/10.1111/gcb.14011",
      "authors": "Freitas, F. L. M., Guidotti, V., Sparovek, G., & Hamamura, C.",
      "published": "2018",
      "image": "assets/hotsite/images/articles/nota_tecnica_malha_fundiaria_do_brasil.png",
      "pt": {
        "title": "Nota técnica: Malha fundiária do Brasil, v.1812",
        "abstract": "A malha fundiária do Brasil é resultado de uma colaboração entre o Imaflora, o GeoLab da Esalq/USP, o Royal Institute of Technology (KTH-Suécia) e o Instituto Federal de Educação, Ciência e Tecnologia de São Paulo. Esta base de dados georreferenciada possui abrangência nacional, oferecendo aberta e publicamente uma visão do conjunto das terras públicas e dos imóveis privados do país. Essa malha fundiária é uma atualização de estudos anteriores realizados pela equipe do Professor Gerd Sparovek - GeoLab da Esalq / USP, além do desenvolvimento de novas funcionalidades e a codificação de uma rotina que permite a atualização permanente desta base."
      },
      "en": {
        "title": "Technical note: Land tenure dataset of Brazil, v.1812",
        "abstract": "The land tenure dataset of Brazil is the result of a collaboration between Imaflora, GeoLab from Esalq/USP, the Royal Institute of Technology (KTH-Sweden), and the Federal Institute of Education, Science, and Technology of São Paulo. This georeferenced database has a national scope, offering an open and public view of the set of public lands and private properties in the country. This land tenure grid is an update of previous studies conducted by Professor Gerd Sparovek's team - GeoLab from Esalq / USP, in addition to developing new functionalities and coding a routine that allows permanent updates to this database."
      }
    },
    {
      "doi": "https://www.cartasdaterra.com.br/post/malha-fundiaria-2025",
      "authors": "Coutinho, P. A. Q., Scarabello, M. C., & Fernandes, P. G.",
      "published": "2026",
      "image": "assets/hotsite/images/articles/malha_fundiaria_nota_tecnica_2025_2a_edicao.png",
      "pt": {
        "title": "Malha Fundiária: Nota Técnica 2025, 2ª Edição",
        "abstract": "A Malha Fundiária do Brasil é uma base de dados geoespacial de abrangência nacional desenvolvida em colaboração entre o Grupo de Políticas Públicas da ESALQ/USP (GPP), o Instituto para Governança Territorial e Políticas Públicas (iGPP) e o Imaflora. O mapeamento organiza o território a partir de dimensões de uso, acesso e domínio, subdividindo o país em categorias fundiárias e integrando o cruzamento espacial com o Cadastro Ambiental Rural (CAR). Esta segunda edição introduz a transição metodológica para o modelo vetorial em PostGIS, otimizando a precisão geométrica e o rastreamento completo de sobreposições territoriais para subsidiar políticas públicas."
      },
      "en": {
        "title": "Land Tenure Dataset: Technical Note 2025, 2nd Edition",
        "abstract": "The Land Tenure Dataset of Brazil is a nationwide geospatial database developed through a collaboration between the Public Policy Group at ESALQ/USP (GPP), the Institute for Territorial Governance and Public Policies (iGPP), and Imaflora. This mapping structures the national territory based on land use, access, and tenure dimensions, subdividing the country into land tenure categories while integrating spatial cross-referencing with the Rural Environmental Registry (CAR). This second edition introduces a methodological transition to a PostGIS vector model, optimizing geometric precision and the complete tracking of territorial overlaps to support public policies."
      }
    },
    {
      "doi": "https://www.cartasdaterra.com.br/post/modelagem-espacial-da-lpvn",
      "authors": "Alves dos Santos, H. L. R., Fernandes, P. G., Scarabello, M. C., Coutinho, P. A. Q., & Marinho, J. V. L.",
      "published": "2025",
      "image": "assets/hotsite/images/articles/lei_de_protecao_da_vegetacao_nativa_modelagem_espacial_de_alta_resolucao_2025.png",
      "pt": {
        "title": "Lei de Proteção da Vegetação Nativa: modelagem espacial de alta resolução - Nota técnica e metodológica atualização 2025",
        "abstract": "Esta nota técnica apresenta conceitos, métodos e resultados das estimativas sobre o cumprimento da Lei de Proteção da Vegetação Nativa (LPVN - Lei nº 12.651/2012) nos imóveis rurais do Brasil através de uma modelagem espacial vetorial de alta resolução baseada no CAR. Os resultados indicam que a área agregada de déficit de Áreas de Preservação Permanente (APP) e Reserva Legal (RL) representa cerca de 3,7% da área total ocupada por imóveis rurais, um valor cinco vezes menor que o excedente de vegetação nativa calculado. Além disso, as análises revelam uma alta concentração geográfica dos passivos e ativos ambientais, demonstrando que os problemas de sobreposições de cadastros não impedem o avanço na implementação da lei."
      },
      "en": {
        "title": "Native Vegetation Protection Law: high-resolution spatial modeling - Technical and methodological note 2025 update",
        "abstract": "This technical note presents the concepts, methods, and results of estimated compliance with the Native Vegetation Protection Law (LPVN - Law No. 12,651/2012) across Brazilian rural properties using a high-resolution vector spatial modeling based on the CAR database. The results show that the aggregate deficit area of Permanent Preservation Areas (APP) and Legal Reserves (RL) represents approximately 3.7% of the total land occupied by rural properties, a magnitude five times lower than the calculated native vegetation surplus. Furthermore, the analysis reveals a high geographical concentration of both environmental liabilities and assets, demonstrating that topological registry overlaps in the CAR system are not a barrier to accelerating the implementation of the law."
      }
    },
    {
      "doi": "https://admin.imaflora.org/public/media/biblioteca/nota_tecnica_-_final.pdf",
      "authors": "Cerignoni, F.",
      "published": "2023-09-01",
      "image": "assets/hotsite/images/articles/malha_car_livre_de_sobreposicao.png",
      "pt": {
        "title": "Nota Técnica: Malha CAR Livre de Sobreposição",
        "abstract": "A criação do Cadastro Ambiental Rural (CAR) foi um avanço para o diagnóstico ambiental e planejamento de propriedades rurais no Brasil. No entanto, devido ao caráter autodeclaratório e à metodologia de registro, existem muitas sobreposições entre imóveis que dificultam análises em escalas regionais. Essa nota descreve a metodologia para a limpeza das sobreposições do CAR em todo o território nacional."
      },
      "en": {
        "title": "Technical Note: CAR Mesh Free of Overlaps",
        "abstract": "The creation of the Rural Environmental Registry (CAR) was an advance for environmental diagnosis and rural property planning in Brazil. However, due to its self-declaratory nature and registration methodology, there are many overlaps between properties that hinder regional-scale analyses. This note describes the methodology for cleaning CAR overlaps throughout the national territory."
      }
    }
  ];

  constructor(private localizationService: LocalizationService) {
    this.lang = this.localizationService.currentLang();
    this.updateArticles();
  }

  ngOnInit() {
    this.localizationService.translateService.onLangChange.subscribe((langChangeEvent: LangChangeEvent) => {
      this.lang = langChangeEvent.lang;
      this.updateArticles();
    });
  }

  private updateArticles(): void {
    const language = this.lang === 'pt' ? 'pt' : 'en';
    
    this.articles = this.allArticles.map(article => ({
      title: article[language].title,
      abstract: article[language].abstract,
      doi: article.doi,
      authors: article.authors,
      published: article.published,
      image: article.image
    }));

    this.articles = this.articles.sort((a, b) => (a.published > b.published) ? -1 : 1);
  }
}