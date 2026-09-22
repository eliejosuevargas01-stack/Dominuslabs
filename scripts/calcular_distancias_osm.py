#!/usr/bin/env python3
"""
Calcula distancias rodoviarias entre uma origem e 48 regioes de Gaspar/SC.

O script usa apenas a biblioteca padrao do Python e nao exige chave de API:

* Nominatim localiza o endereco de origem (uma consulta, com cache local).
* OSRM calcula distancia e duracao de todas as rotas em uma matriz 1 x N.
* CSV e JSON preservam tambem os tempos e valores informados pelo usuario.

IMPORTANTE SOBRE OS SERVICOS PUBLICOS
=====================================
Nominatim publico: maximo absoluto de 1 requisicao/segundo, User-Agent proprio,
cache obrigatorio e uso leve. Leia antes de usar:
https://operations.osmfoundation.org/policies/nominatim/

O servidor demonstrativo do OSRM aceita apenas uso razoavel e NAO COMERCIAL,
no maximo 1 requisicao/segundo, sem garantia de disponibilidade:
https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server

Para uso comercial ou recorrente, informe uma instancia propria por
``--osrm-url``. O endereco enviado ao Nominatim e as coordenadas enviadas ao
OSRM podem aparecer nos logs dos operadores. Para nao enviar o endereco ao
geocodificador, use ``--origem-lat`` e ``--origem-lon``.

As divisoes ``- 01``, ``- 02`` etc. nao existem como enderecos oficiais no
OpenStreetMap. Por isso, cada uma usa abaixo um ponto representativo editavel.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


ORIGEM_PADRAO = (
    "Rua Rodolfo Vieira Pamplona, 156, Santa Terezinha, Gaspar, SC, Brasil"
)
NOMINATIM_PADRAO = "https://nominatim.openstreetmap.org/search"
OSRM_PADRAO = "https://router.project-osrm.org"
USER_AGENT_BASE = "calculador-distancias-gaspar/2.0"
POLITICA_NOMINATIM = "https://operations.osmfoundation.org/policies/nominatim/"
POLITICA_OSRM = "https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server"
ATRIBUICAO = "© OpenStreetMap contributors (ODbL); rotas calculadas com OSRM."
LINK_COPYRIGHT_OSM = "https://www.openstreetmap.org/copyright"
INTERVALO_PUBLICO_SEGUNDOS = 1.1
TARIFA_POR_KM_BRL = Decimal("1.50")
VALOR_MINIMO_BRL = Decimal("8.00")


@dataclass(frozen=True)
class Destino:
    rotulo: str
    rotulo_normalizado: str
    latitude: float
    longitude: float
    ponto_representativo: str
    tempo_informado_min: int
    valor_informado_brl: float


# Os rotulos originais foram preservados para facilitar a conciliacao com a
# tabela do usuario. Coordenadas sao pontos representativos, nao limites de CEP.
DESTINOS: tuple[Destino, ...] = (
    Destino("Aguas Negras - 01", "Aguas Negras - 01", -26.91200, -48.98810, "Estrada Geral Aguas Negras (inicio/Figueira)", 11, 10.23),
    Destino("Aguas Negras - 02", "Aguas Negras - 02", -26.89500, -48.99500, "Estrada Geral Aguas Negras (meio)", 14, 12.81),
    Destino("Aguas Negras - 03", "Aguas Negras - 03", -26.87800, -49.00200, "Estrada Geral Aguas Negras (fim/fundos)", 15, 18.52),
    Destino("Alto Gasparinho", "Alto Gasparinho", -27.00559, -48.96180, "Alto Gasparinho (centro)", 17, 16.32),
    Destino("Arraial - 1", "Arraial - 01", -26.88500, -48.96500, "Estrada Geral do Arraial (inicio)", 19, 19.07),
    Destino("Arraial - 2", "Arraial - 02", -26.86500, -48.97200, "Estrada Geral do Arraial (meio)", 20, 21.09),
    Destino("Arraial D'ouro", "Arraial D'Ouro", -26.85728, -48.97613, "Arraial do Ouro", 22, 18.34),
    Destino("Barracão", "Barracão", -26.98686, -48.87661, "Barracão (centro)", 23, 19.19),
    Destino("Barracão - 02", "Barracão - 02", -27.01500, -48.86800, "Barracão (fundos/Rua João Barbieri)", 17, 16.77),
    Destino("Bateias", "Bateias", -26.99519, -48.91310, "Bateias (centro)", 12, 14.50),
    Destino("Bela Vista", "Bela Vista", -26.89664, -49.00476, "Bela Vista (centro)", 14, 13.68),
    Destino("Belchior - 1", "Belchior - 01", -26.88500, -49.00200, "Belchior (inicio/BR-470)", 16, 19.93),
    Destino("Belchior Alto", "Belchior Alto", -26.80839, -49.02154, "Belchior Alto (Cascanéia/divisa)", 28, 29.21),
    Destino("Belchior Baixo", "Belchior Baixo", -26.87641, -49.00963, "Belchior Baixo (centro)", 16, 18.41),
    Destino("Belchior Central", "Belchior Central", -26.85575, -49.03556, "Belchior Central", 18, 18.81),
    Destino("Centro", "Centro", -26.93310, -48.95588, "Centro de Gaspar", 5, 8.00),
    Destino("Coloninha", "Coloninha", -26.92796, -48.97069, "Coloninha", 7, 8.00),
    Destino("Figueira", "Figueira", -26.91621, -48.99493, "Figueira", 12, 11.69),
    Destino("Gaspar Alto", "Gaspar Alto", -27.01600, -49.03443, "Gaspar Alto", 30, 22.82),
    Destino("Gaspar Grande - 01", "Gaspar Grande - 01", -26.93800, -48.97500, "Rua Prefeito Leopoldo Schramm (inicio)", 8, 8.00),
    Destino("Gaspar Grande - 02", "Gaspar Grande - 02", -26.94800, -48.99000, "Colégio Frei Godofredo/meio", 11, 10.68),
    Destino("Gaspar Grande - 03", "Gaspar Grande - 03", -26.95961, -49.02015, "Sociedade Cruzeiro", 20, 18.15),
    Destino("Gaspar Grande - 04", "Gaspar Grande - 04", -26.96800, -49.04000, "Cascata Carolina", 33, 21.71),
    Destino("Gaspar Grande - 05", "Gaspar Grande - 05", -26.97800, -49.06000, "Fim da Estrada Geral/Morro do Baú", 30, 23.01),
    Destino("Gaspar Mirim - 01", "Gaspar Mirim - 01", -26.94500, -48.94800, "Rua Frei Canísio (inicio)", 2, 8.00),
    Destino("Gaspar Mirim - 02", "Gaspar Mirim - 02", -26.95243, -48.94715, "Gaspar Mirim (centro)", 3, 8.00),
    Destino("Gasparinho - 01", "Gasparinho - 01", -26.93800, -48.96500, "Rua Frei Solano (inicio)", 7, 8.00),
    Destino("Gasparinho - 02", "Gasparinho - 02", -26.94624, -48.96923, "Capela Santo Antônio", 6, 8.00),
    Destino("Gasparinho - 03", "Gasparinho - 03", -26.96500, -48.96600, "Rua Gasparinho (meio)", 8, 8.12),
    Destino("Gasparinho - 04", "Gasparinho - 04", -26.98500, -48.96300, "Fazzenda Park Hotel", 15, 14.29),
    Destino("Gasparinho - 05", "Gasparinho - 05", -26.99749, -48.95989, "Gasparinho Central", 15, 15.09),
    Destino("Lagoa - 01", "Lagoa - 01", -26.91800, -48.91500, "Rua Lagoa (inicio)", 11, 11.82),
    Destino("Lagoa - 02", "Lagoa - 02", -26.90476, -48.90046, "Lagoa (centro)", 22, 17.57),
    Destino("Lagoa - 03", "Lagoa - 03", -26.89000, -48.88500, "Lagoa (fundos/divisa)", 16, 21.39),
    Destino("Macucos", "Macucos", -26.95755, -48.87294, "Macucos", 16, 16.53),
    Destino("Margem Esquerda - 01", "Margem Esquerda - 01", -26.92500, -48.96000, "Ponte Hercílio Deeke", 5, 8.00),
    Destino("Margem Esquerda - 02", "Margem Esquerda - 02", -26.90530, -48.96073, "Margem Esquerda (centro)", 13, 14.70),
    Destino("Margem Esquerda - 03", "Margem Esquerda - 03", -26.89000, -48.95000, "Fundos/direcao Ilhota", 16, 14.82),
    Destino("Óleo Grande", "Óleo Grande", -26.97839, -48.85770, "Óleo Grande", 20, 18.76),
    Destino("Pocinho", "Pocinho", -26.89467, -48.84794, "Pocinho/Ribeirão Pocinho", 21, 20.36),
    Destino("Poço Grande - 01", "Poço Grande - 01", -26.93000, -48.92500, "Início da Rodovia Jorge Lacerda", 6, 8.00),
    Destino("Poço Grande - 02", "Poço Grande - 02", -26.92154, -48.90603, "Poço Grande (centro)", 12, 12.25),
    Destino("Poço Grande 03 -", "Poço Grande - 03", -26.94537, -48.87387, "Fundos do Poço Grande", 16, 17.12),
    Destino("Santa Teresinha - 02", "Santa Teresinha - 02", -26.94200, -48.93500, "Rua Rodolfo Vieira Pamplona (meio)", 4, 8.00),
    Destino("Santa Teresinha - 03", "Santa Teresinha - 03", -26.94616, -48.92510, "Santa Terezinha (leste)", 5, 8.00),
    Destino("Santa Terezinha", "Santa Terezinha", -26.93850, -48.94650, "Base/ponto zero da regiao", 1, 8.00),
    Destino("Sertão Verde", "Sertão Verde", -26.91302, -48.97245, "Sertão Verde", 9, 9.25),
    Destino("Sete de Setembro", "Sete de Setembro", -26.92747, -48.94246, "Sete de Setembro", 4, 8.00),
)


class ErroServico(RuntimeError):
    """Falha legivel ao consultar Nominatim ou OSRM."""


class LimitadorTaxa:
    def __init__(self, intervalo_segundos: float) -> None:
        self.intervalo_segundos = intervalo_segundos
        self._ultima_requisicao: float | None = None

    def aguardar(self) -> None:
        agora = time.monotonic()
        if self._ultima_requisicao is not None:
            restante = self.intervalo_segundos - (agora - self._ultima_requisicao)
            if restante > 0:
                time.sleep(restante)
        self._ultima_requisicao = time.monotonic()


def criar_user_agent(contato: str | None) -> str:
    if contato and contato.strip():
        return f"{USER_AGENT_BASE} (contato: {contato.strip()})"
    return USER_AGENT_BASE


def requisitar_json(
    url: str,
    *,
    user_agent: str,
    timeout: float,
    limitador: LimitadorTaxa,
    tentativas: int = 3,
    aceitar_json_http_400: bool = False,
) -> Any:
    ultimo_erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        limitador.aguardar()
        requisicao = Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        )
        try:
            with urlopen(requisicao, timeout=timeout) as resposta:
                return json.loads(resposta.read().decode("utf-8"))
        except HTTPError as erro:
            ultimo_erro = erro
            corpo = erro.read()
            if aceitar_json_http_400 and erro.code == 400:
                try:
                    resposta_erro = json.loads(corpo.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    resposta_erro = None
                if isinstance(resposta_erro, dict):
                    return resposta_erro
            recuperavel = erro.code == 429 or 500 <= erro.code <= 599
            if not recuperavel or tentativa == tentativas:
                detalhe = corpo[:500].decode("utf-8", errors="replace")
                raise ErroServico(
                    f"HTTP {erro.code} ao consultar {urlparse(url).netloc}: {detalhe}"
                ) from erro
            retry_after = erro.headers.get("Retry-After", "")
            espera = float(retry_after) if retry_after.isdigit() else 2**tentativa
            time.sleep(max(espera, INTERVALO_PUBLICO_SEGUNDOS))
        except (URLError, TimeoutError, json.JSONDecodeError) as erro:
            ultimo_erro = erro
            if tentativa == tentativas:
                raise ErroServico(
                    f"Falha ao consultar {urlparse(url).netloc}: {erro}"
                ) from erro
            time.sleep(2**tentativa)
    raise ErroServico(f"Falha inesperada de rede: {ultimo_erro}")


def carregar_cache(caminho: Path) -> dict[str, Any]:
    if not caminho.exists():
        return {"versao": 1, "itens": {}}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(dados, dict) or not isinstance(dados.get("itens"), dict):
            raise ValueError("formato invalido")
        return dados
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        print(f"AVISO: cache ignorado ({caminho}): {erro}", file=sys.stderr)
        return {"versao": 1, "itens": {}}


def gravar_json_atomico(caminho: Path, dados: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=caminho.parent,
            prefix=f".{caminho.name}.",
            suffix=".tmp",
            delete=False,
        ) as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
            temporario = Path(arquivo.name)
        temporario.replace(caminho)
    except Exception:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
        raise


def chave_normalizada(texto: str) -> str:
    return " ".join(texto.casefold().split())


def numero_solicitado(endereco: str) -> str | None:
    encontrado = re.search(r"\b(\d{1,6}[a-zA-Z]?)\b", endereco)
    return encontrado.group(1).casefold() if encontrado else None


def geocodificar_origem(
    endereco: str,
    *,
    nominatim_url: str,
    user_agent: str,
    contato: str | None,
    timeout: float,
    cache_path: Path,
    atualizar_cache: bool,
) -> dict[str, Any]:
    cache = carregar_cache(cache_path)
    chave_endereco = chave_normalizada(endereco)
    chave = chave_normalizada(f"{nominatim_url}|{endereco}")
    if not atualizar_cache and chave in cache["itens"]:
        resultado = dict(cache["itens"][chave])
        resultado["origem_dados"] = "cache"
        return resultado

    parametros = {
        "q": endereco,
        "format": "jsonv2",
        "limit": 5,
        "countrycodes": "br",
        "addressdetails": 1,
        "accept-language": "pt-BR",
    }
    if contato and contato.strip():
        parametros["email"] = contato.strip()
    url = f"{nominatim_url.rstrip('?')}?{urlencode(parametros)}"
    respostas = requisitar_json(
        url,
        user_agent=user_agent,
        timeout=timeout,
        limitador=LimitadorTaxa(INTERVALO_PUBLICO_SEGUNDOS),
    )
    if not isinstance(respostas, list) or not respostas:
        raise ErroServico(
            "O Nominatim nao encontrou a origem. Informe coordenadas com "
            "--origem-lat e --origem-lon."
        )

    candidatos = [item for item in respostas if isinstance(item, dict)]
    if not candidatos:
        raise ErroServico("O Nominatim devolveu uma resposta sem candidatos validos")

    consulta_gaspar = "gaspar" in chave_endereco
    consulta_santa_catarina = (
        "santa catarina" in chave_endereco
        or re.search(r"(?:^|[ ,])sc(?:[ ,]|$)", chave_endereco) is not None
    )
    if chave_endereco == chave_normalizada(ORIGEM_PADRAO) or consulta_gaspar:
        em_gaspar = [
            item
            for item in candidatos
            if "gaspar" in chave_normalizada(item.get("display_name", ""))
        ]
        if consulta_santa_catarina:
            em_gaspar = [
                item
                for item in em_gaspar
                if "santa catarina" in chave_normalizada(item.get("display_name", ""))
            ]
        if not em_gaspar:
            raise ErroServico(
                "O Nominatim encontrou candidatos, mas nenhum corresponde a Gaspar/SC. "
                "Confira o endereco ou use --origem-lat e --origem-lon."
            )
        candidatos = em_gaspar
    escolhido = candidatos[0]
    endereco_osm = escolhido.get("address") or {}
    solicitado = numero_solicitado(endereco)
    encontrado = str(endereco_osm.get("house_number", "")).casefold() or None
    precisao = (
        "numero_exato"
        if solicitado and encontrado == solicitado
        else "rua_ou_area_aproximada"
    )
    resultado = {
        "latitude": float(escolhido["lat"]),
        "longitude": float(escolhido["lon"]),
        "endereco_resolvido": escolhido.get("display_name", endereco),
        "precisao": precisao,
        "numero_solicitado": solicitado,
        "numero_encontrado": encontrado,
        "osm_type": escolhido.get("osm_type"),
        "osm_id": escolhido.get("osm_id"),
        "geocodificado_em": datetime.now(timezone.utc).isoformat(),
        "origem_dados": "nominatim",
    }
    cache["itens"][chave] = resultado
    gravar_json_atomico(cache_path, cache)
    return resultado


def validar_coordenada(latitude: float, longitude: float, contexto: str) -> None:
    if not -90 <= latitude <= 90:
        raise ValueError(f"Latitude invalida em {contexto}: {latitude}")
    if not -180 <= longitude <= 180:
        raise ValueError(f"Longitude invalida em {contexto}: {longitude}")


def validar_destinos(destinos: Sequence[Destino]) -> None:
    if len(destinos) != 48:
        raise ValueError(f"Esperados 48 destinos; encontrados {len(destinos)}")
    rotulos: set[str] = set()
    for destino in destinos:
        chave = chave_normalizada(destino.rotulo)
        if chave in rotulos:
            raise ValueError(f"Destino duplicado: {destino.rotulo}")
        rotulos.add(chave)
        validar_coordenada(destino.latitude, destino.longitude, destino.rotulo)
        if destino.tempo_informado_min < 0 or destino.valor_informado_brl < 0:
            raise ValueError(f"Referencia negativa em {destino.rotulo}")


def distancia_reta_km(
    origem_lat: float,
    origem_lon: float,
    destino_lat: float,
    destino_lon: float,
) -> float:
    raio_terra_km = 6371.0088
    lat1, lat2 = math.radians(origem_lat), math.radians(destino_lat)
    delta_lat = math.radians(destino_lat - origem_lat)
    delta_lon = math.radians(destino_lon - origem_lon)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return raio_terra_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def separar_lotes(itens: Sequence[Destino], tamanho: int) -> Iterable[Sequence[Destino]]:
    for inicio in range(0, len(itens), tamanho):
        yield itens[inicio : inicio + tamanho]


def consultar_lote_osrm(
    origem: tuple[float, float],
    destinos: Sequence[Destino],
    *,
    osrm_url: str,
    user_agent: str,
    timeout: float,
    limitador: LimitadorTaxa,
    cache: dict[str, Any],
    atualizar_cache: bool,
) -> dict[str, Any]:
    coordenadas = [origem] + [(item.latitude, item.longitude) for item in destinos]
    assinatura = {
        "osrm_url": osrm_url.rstrip("/"),
        "perfil": "driving",
        "coordenadas": [[round(lat, 7), round(lon, 7)] for lat, lon in coordenadas],
    }
    chave = hashlib.sha256(
        json.dumps(assinatura, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if not atualizar_cache and chave in cache["itens"]:
        return dict(cache["itens"][chave])

    trecho_coordenadas = ";".join(
        f"{longitude:.7f},{latitude:.7f}" for latitude, longitude in coordenadas
    )
    parametros = urlencode(
        {
            "sources": "0",
            "destinations": ";".join(str(i) for i in range(1, len(coordenadas))),
            "annotations": "distance,duration",
        }
    )
    url = (
        f"{osrm_url.rstrip('/')}/table/v1/driving/"
        f"{trecho_coordenadas}?{parametros}"
    )
    dados = requisitar_json(
        url,
        user_agent=user_agent,
        timeout=timeout,
        limitador=limitador,
        aceitar_json_http_400=True,
    )
    if isinstance(dados, dict) and dados.get("code") == "Ok":
        cache["itens"][chave] = dados
    return dados


def extrair_lote_osrm(
    dados: dict[str, Any], destinos: Sequence[Destino]
) -> list[dict[str, Any]]:
    codigo = dados.get("code")
    if codigo != "Ok":
        mensagem = dados.get("message", "sem detalhes")
        raise ErroServico(f"OSRM retornou {codigo}: {mensagem}")
    distancias = dados.get("distances")
    duracoes = dados.get("durations")
    pontos_ajustados = dados.get("destinations") or []
    if (
        not isinstance(distancias, list)
        or not distancias
        or not isinstance(duracoes, list)
        or not duracoes
        or len(distancias[0]) != len(destinos)
        or len(duracoes[0]) != len(destinos)
    ):
        raise ErroServico("Resposta incompleta ou inesperada do OSRM")

    rotas: list[dict[str, Any]] = []
    for indice, destino in enumerate(destinos):
        distancia_m = distancias[0][indice]
        duracao_s = duracoes[0][indice]
        ponto_ajustado = (
            pontos_ajustados[indice]
            if indice < len(pontos_ajustados) and pontos_ajustados[indice]
            else {}
        )
        rotas.append(
            {
                "destino": destino,
                "distancia_m": distancia_m,
                "duracao_s": duracao_s,
                "distancia_ate_via_m": ponto_ajustado.get("distance"),
            }
        )
    return rotas


def calcular_rotas_osrm(
    origem: tuple[float, float],
    destinos: Sequence[Destino],
    *,
    osrm_url: str,
    user_agent: str,
    timeout: float,
    tamanho_lote: int,
    cache_path: Path,
    atualizar_cache: bool,
) -> list[dict[str, Any]]:
    cache = carregar_cache(cache_path)
    limitador = LimitadorTaxa(INTERVALO_PUBLICO_SEGUNDOS)

    def processar_lote(lote: Sequence[Destino]) -> list[dict[str, Any]]:
        dados = consultar_lote_osrm(
            origem,
            lote,
            osrm_url=osrm_url,
            user_agent=user_agent,
            timeout=timeout,
            limitador=limitador,
            cache=cache,
            atualizar_cache=atualizar_cache,
        )
        if isinstance(dados, dict) and dados.get("code") == "TooBig":
            if len(lote) == 1:
                raise ErroServico(
                    "O limite do servidor OSRM e menor que uma origem e um destino"
                )
            metade = max(1, len(lote) // 2)
            esquerda = processar_lote(lote[:metade])
            direita = processar_lote(lote[metade:])
            return esquerda + direita

        rotas = extrair_lote_osrm(dados, lote)
        # Persiste cada lote concluido para nao repeti-lo se outro lote falhar.
        gravar_json_atomico(cache_path, cache)
        return rotas

    todas: list[dict[str, Any]] = []
    for lote in separar_lotes(destinos, tamanho_lote):
        todas.extend(processar_lote(lote))
    gravar_json_atomico(cache_path, cache)
    return todas


def montar_resultados(
    origem: tuple[float, float], rotas: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    resultados: list[dict[str, Any]] = []
    for identificador, rota in enumerate(rotas, start=1):
        destino: Destino = rota["destino"]
        distancia_m = rota["distancia_m"]
        duracao_s = rota["duracao_s"]
        distancia_km = None if distancia_m is None else round(distancia_m / 1000, 2)
        tempo_osrm = None if duracao_s is None else round(duracao_s / 60, 1)
        diferenca_tempo = (
            None
            if tempo_osrm is None
            else round(tempo_osrm - destino.tempo_informado_min, 1)
        )
        if distancia_m is None:
            valor_bruto = None
            valor_calculado = None
            diferenca_valor = None
            regra_aplicada = "sem_rota"
        else:
            # Usa a mesma distancia de duas casas exibida no CSV, permitindo
            # conferir manualmente o calculo: distancia_rota_km x R$ 1,50.
            valor_bruto_decimal = Decimal(str(distancia_km)) * TARIFA_POR_KM_BRL
            valor_bruto = float(
                valor_bruto_decimal.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            )
            valor_decimal = max(valor_bruto_decimal, VALOR_MINIMO_BRL).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            valor_calculado = float(valor_decimal)
            regra_aplicada = (
                "valor_minimo_R$8,00"
                if valor_bruto_decimal < VALOR_MINIMO_BRL
                else "R$1,50_por_km"
            )
            diferenca_valor = float(
                (valor_decimal - Decimal(str(destino.valor_informado_brl))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            )
        resultados.append(
            {
                "id": identificador,
                "cidade": "Gaspar",
                "destino": destino.rotulo,
                "destino_normalizado": destino.rotulo_normalizado,
                "ponto_representativo": destino.ponto_representativo,
                "status": "OK" if distancia_m is not None and duracao_s is not None else "SEM_ROTA",
                "distancia_rota_km": distancia_km,
                "distancia_reta_km": round(
                    distancia_reta_km(
                        origem[0], origem[1], destino.latitude, destino.longitude
                    ),
                    2,
                ),
                "tempo_osrm_min": tempo_osrm,
                "tempo_informado_min": destino.tempo_informado_min,
                "diferenca_tempo_min": diferenca_tempo,
                "tarifa_por_km_brl": float(TARIFA_POR_KM_BRL),
                "valor_bruto_brl": valor_bruto,
                "valor_minimo_brl": float(VALOR_MINIMO_BRL),
                "valor_anterior_brl": destino.valor_informado_brl,
                "valor_calculado_brl": valor_calculado,
                "diferenca_valor_brl": diferenca_valor,
                "regra_preco_aplicada": regra_aplicada,
                "latitude_destino": destino.latitude,
                "longitude_destino": destino.longitude,
                "distancia_ponto_ate_via_osrm_m": rota["distancia_ate_via_m"],
            }
        )
    return resultados


def decimal_csv(valor: Any, casas: int = 2) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:.{casas}f}".replace(".", ",")
    return str(valor)


def gravar_csv(caminho: Path, resultados: Sequence[dict[str, Any]]) -> None:
    campos = list(resultados[0].keys())
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
        escritor.writeheader()
        for resultado in resultados:
            linha = dict(resultado)
            for campo, casas in {
                "distancia_rota_km": 2,
                "distancia_reta_km": 2,
                "tempo_osrm_min": 1,
                "diferenca_tempo_min": 1,
                "tarifa_por_km_brl": 2,
                "valor_bruto_brl": 2,
                "valor_minimo_brl": 2,
                "valor_anterior_brl": 2,
                "valor_calculado_brl": 2,
                "diferenca_valor_brl": 2,
                "latitude_destino": 6,
                "longitude_destino": 6,
                "distancia_ponto_ate_via_osrm_m": 1,
            }.items():
                linha[campo] = decimal_csv(linha[campo], casas)
            escritor.writerow(linha)


def imprimir_tabela(resultados: Sequence[dict[str, Any]]) -> None:
    print()
    print(f"{'#':>2}  {'DESTINO':<27} {'KM ROTA':>8} {'MIN OSRM':>9} {'VALOR NOVO':>12}")
    print("-" * 68)
    for item in resultados:
        distancia = "--" if item["distancia_rota_km"] is None else f"{item['distancia_rota_km']:.2f}"
        tempo = "--" if item["tempo_osrm_min"] is None else f"{item['tempo_osrm_min']:.1f}"
        print(
            f"{item['id']:>2}  {item['destino'][:27]:<27} {distancia:>8} "
            f"{tempo:>9} R$ {item['valor_calculado_brl']:>8.2f}"
        )


def eh_servidor_demo_publico(osrm_url: str) -> bool:
    host = (urlparse(osrm_url).hostname or "").casefold()
    return host in {"router.project-osrm.org", "routing.openstreetmap.de"}


def criar_parser() -> argparse.ArgumentParser:
    descricao = """\
Calcula a distancia de carro da origem ate 48 pontos representativos de Gaspar.
Gera CSV (separador ';', decimal ',') e JSON, sem dependencias externas.
"""
    epilogo = f"""\
Politica obrigatoria do Nominatim: {POLITICA_NOMINATIM}
Politica do demo OSRM (somente uso razoavel e nao comercial): {POLITICA_OSRM}

Exemplo com geocodificacao:
  python3 scripts/calcular_distancias_osm.py

Exemplo sem enviar o endereco ao Nominatim:
  python3 scripts/calcular_distancias_osm.py --origem-lat -26.9385 --origem-lon -48.9465
"""
    parser = argparse.ArgumentParser(
        description=descricao,
        epilog=epilogo,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--origem", default=ORIGEM_PADRAO, help="Endereco de origem")
    parser.add_argument("--origem-lat", type=float, help="Latitude exata da origem")
    parser.add_argument("--origem-lon", type=float, help="Longitude exata da origem")
    parser.add_argument(
        "--diretorio-saida", type=Path, default=Path("."), help="Pasta para CSV/JSON"
    )
    parser.add_argument(
        "--prefixo-saida",
        default="distancias_gaspar_calculadas",
        help="Nome-base das saidas",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache_distancias_osm"),
        help="Pasta do cache persistente",
    )
    parser.add_argument(
        "--nominatim-url", default=NOMINATIM_PADRAO, help="Endpoint de geocodificacao"
    )
    parser.add_argument(
        "--osrm-url", default=OSRM_PADRAO, help="Servidor OSRM (use instancia propria em producao)"
    )
    parser.add_argument(
        "--contato", help="Email ou URL real para identificar o cliente aos operadores"
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout HTTP em segundos")
    parser.add_argument(
        "--tamanho-lote",
        type=int,
        default=48,
        help="Destinos por consulta OSRM; padrao: todos em uma chamada",
    )
    parser.add_argument(
        "--atualizar-cache", action="store_true", help="Ignora respostas salvas e consulta novamente"
    )
    parser.add_argument(
        "--somente-validar", action="store_true", help="Valida os 48 destinos sem acessar a internet"
    )
    return parser


def executar(argumentos: Sequence[str] | None = None) -> int:
    parser = criar_parser()
    args = parser.parse_args(argumentos)
    if (args.origem_lat is None) != (args.origem_lon is None):
        parser.error("--origem-lat e --origem-lon devem ser usados juntos")
    if args.timeout <= 0:
        parser.error("--timeout deve ser maior que zero")
    if args.tamanho_lote <= 0:
        parser.error("--tamanho-lote deve ser maior que zero")

    try:
        validar_destinos(DESTINOS)
        if args.somente_validar:
            print(f"OK: {len(DESTINOS)} destinos unicos e coordenadas validas.")
            return 0

        user_agent = criar_user_agent(args.contato)
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        if args.origem_lat is not None:
            validar_coordenada(args.origem_lat, args.origem_lon, "origem")
            origem_dados = {
                "latitude": args.origem_lat,
                "longitude": args.origem_lon,
                "endereco_resolvido": "Coordenadas informadas pelo usuario",
                "precisao": "coordenadas_informadas",
                "origem_dados": "argumentos",
            }
        else:
            print(
                "AVISO DE PRIVACIDADE: se nao estiver no cache, o endereco de origem "
                "sera enviado ao Nominatim.\n"
                f"Politica obrigatoria: {POLITICA_NOMINATIM}"
            )
            origem_dados = geocodificar_origem(
                args.origem,
                nominatim_url=args.nominatim_url,
                user_agent=user_agent,
                contato=args.contato,
                timeout=args.timeout,
                cache_path=args.cache_dir / "geocodificacao.json",
                atualizar_cache=args.atualizar_cache,
            )

        origem = (origem_dados["latitude"], origem_dados["longitude"])
        if origem_dados["precisao"] == "rua_ou_area_aproximada":
            print(
                "AVISO: o OSM nao confirmou o numero do imovel; foi usado o ponto "
                "retornado para a rua/area. Use --origem-lat/--origem-lon para precisao exata.",
                file=sys.stderr,
            )
        print(f"Origem resolvida: {origem_dados['endereco_resolvido']}")
        print(f"Coordenadas: {origem[0]:.7f}, {origem[1]:.7f}")

        if eh_servidor_demo_publico(args.osrm_url):
            print(
                "AVISO: o OSRM publico e apenas para uso razoavel e NAO COMERCIAL.\n"
                f"Politica: {POLITICA_OSRM}\n"
                "Para uso operacional/comercial, configure --osrm-url com uma instancia propria."
            )

        rotas = calcular_rotas_osrm(
            origem,
            DESTINOS,
            osrm_url=args.osrm_url,
            user_agent=user_agent,
            timeout=args.timeout,
            tamanho_lote=min(args.tamanho_lote, len(DESTINOS)),
            cache_path=args.cache_dir / "rotas_osrm.json",
            atualizar_cache=args.atualizar_cache,
        )
        resultados = montar_resultados(origem, rotas)
        imprimir_tabela(resultados)

        args.diretorio_saida.mkdir(parents=True, exist_ok=True)
        caminho_csv = args.diretorio_saida / f"{args.prefixo_saida}.csv"
        caminho_json = args.diretorio_saida / f"{args.prefixo_saida}.json"
        gravar_csv(caminho_csv, resultados)
        documento_json = {
            "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
            "origem_solicitada": (
                args.origem if args.origem_lat is None else "coordenadas informadas"
            ),
            "origem": origem_dados,
            "quantidade_destinos": len(resultados),
            "tarifa_por_km_brl": float(TARIFA_POR_KM_BRL),
            "valor_minimo_brl": float(VALOR_MINIMO_BRL),
            "regra_de_preco": (
                "valor = max(distancia rodoviaria arredondada a 2 casas x R$ 1,50, R$ 8,00); "
                "arredondamento monetario de meio centavo para cima; sem desconto"
            ),
            "metodologia": (
                "Distancia e duracao da rota mais rapida segundo o perfil driving do OSRM; "
                "nao e necessariamente a menor distancia viaria."
            ),
            "observacao_setores": (
                "Setores 01/02/etc. usam pontos representativos editaveis porque nao sao "
                "enderecos distintos no OpenStreetMap."
            ),
            "atribuicao": ATRIBUICAO,
            "copyright_osm": LINK_COPYRIGHT_OSM,
            "politica_nominatim": POLITICA_NOMINATIM,
            "politica_osrm_demo": POLITICA_OSRM,
            "servidor_osrm": args.osrm_url,
            "resultados": resultados,
        }
        gravar_json_atomico(caminho_json, documento_json)
        print(f"\nArquivos gerados:\n- {caminho_csv.resolve()}\n- {caminho_json.resolve()}")
        print(f"\n{ATRIBUICAO}\n{LINK_COPYRIGHT_OSM}")
        return 0
    except (ErroServico, OSError, ValueError, KeyError, TypeError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(executar())
