from typing import List

from sqlalchemy import text

from .db import engine, get_modalidades, get_paises, get_palpites, get_users

PODIO_COMPLETO_PONTOS = 5
POS_CORRETA_PONTOS = 3
POS_ERRADA_PONTOS = 1


def true_counter(comps: List[bool]) -> int:
    return len([c for c in comps if c])


def update_total_pontos(usuario_id: int, total_pontos: int):
    update_stmt = text(
        """
        UPDATE usuarios 
        SET total_pontos = :total_pontos
        WHERE usuario_id = :usuario_id;
        """
    )
    engine.execute(
        update_stmt, **{"usuario_id": usuario_id, "total_pontos": int(total_pontos)},
    )


def apuracao() -> str:
    apuracao = ""

    users = get_users()
    modalidades = {
        m.modalidade_id: [m.pais_ouro, m.pais_prata, m.pais_bronze, m.modalidade_nome]
        for m in get_modalidades()
    }
    paises_dict = {p.pais_id: p.pais_nome for p in get_paises()}

    for user in users:
        pontos_poss_correta = 0
        pontos_poss_errada = 0
        bonus_podio_completo = 0
        apuracao = apuracao + f"\nProcessando usuário {user.usuario_nome}\n"
        palpites = get_palpites(user.usuario_id)
        for palpite_mod, u_ouro, u_prata, u_bronze in palpites:
            r_ouro, r_prata, r_bronze, m_nome = modalidades[palpite_mod]
            comparacao_one_to_one = [r_ouro == u_ouro, r_prata == u_prata, r_bronze == u_bronze]

            # Bonus de podio completo
            if all(comparacao_one_to_one):
                rodada_podio_completo = PODIO_COMPLETO_PONTOS
                rodada_poss_correta = POS_CORRETA_PONTOS * 3
                rodada_poss_errada = 0
            else:
                rodada_podio_completo = 0

                rodada_poss_correta = POS_CORRETA_PONTOS * true_counter(comparacao_one_to_one)

                ouro_em_outra = POS_ERRADA_PONTOS * true_counter(
                    [u_ouro == r_prata, u_ouro == r_bronze]
                )
                prata_em_outra = POS_ERRADA_PONTOS * true_counter(
                    [u_prata == r_ouro, u_prata == r_bronze]
                )
                bronze_em_outra = POS_ERRADA_PONTOS * true_counter(
                    [u_bronze == r_ouro, u_bronze == r_prata]
                )

                rodada_poss_errada = ouro_em_outra + prata_em_outra + bronze_em_outra

            pontos_poss_correta = pontos_poss_correta + rodada_poss_correta
            pontos_poss_errada = pontos_poss_errada + rodada_poss_errada
            bonus_podio_completo = bonus_podio_completo + rodada_podio_completo

            apuracao = f"""{apuracao}
            Modalidade {m_nome}
            {user.usuario_nome} vs Resultado:
            Ouro:\t{paises_dict.get(u_ouro, "Não registrado")}\t=>\t{paises_dict.get(r_ouro, "Não registrado")}
            Prata:\t{paises_dict.get(u_prata, "Não registrado")}\t=>\t{paises_dict.get(r_prata, "Não registrado")}
            Bronze:\t{paises_dict.get(u_bronze, "Não registrado")}\t=>\t{paises_dict.get(r_bronze, "Não registrado")}

            Pontos ganhos por posição correta: {rodada_poss_correta}
            Pontos ganhos por posição errada: {rodada_poss_errada}
            Pontos ganhos bonus pódio cravado: {rodada_podio_completo}
            Total acumulado: {pontos_poss_correta + pontos_poss_errada + bonus_podio_completo}
            """

        total = pontos_poss_correta + pontos_poss_errada + bonus_podio_completo
        update_total_pontos(user.usuario_id, total)

    return apuracao
