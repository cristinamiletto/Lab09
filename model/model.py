from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # TODO: Aggiungere eventuali altri attributi
        self._escursioni_parco = []  # escursioni del parco selezionato (candidate)
        self._max_giorni = None  # vincolo sui giorni (None = nessun limite)
        self._max_budget = None  # vincolo sul budget (None = nessun limite)

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        # TODO
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()

        for relazione in relazioni:
            # Dagli id (stringhe) ricavo i due oggetti, grazie alle mappe già caricate
            escursione = self.escursioni_map[relazione["id_escursione"]]
            punto = self.punti_interesse_map[relazione["id_punto_interesse"]]

            # Collego i due oggetti in entrambe le direzioni (relazione N:N)
            escursione.punti_interesse.add(punto)
            punto.escursioni.add(escursione)

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        # TODO
        # Salvo i vincoli come attributi, così non devo passarli a ogni chiamata ricorsiva
        self._max_giorni = max_giorni
        self._max_budget = max_budget

        # Tengo solo le escursioni del parco scelto (ordinate per id: risultato deterministico)
        self._escursioni_parco = sorted(
            [e for e in self.escursioni_map.values() if e.id_parco == id_parco],
            key=lambda e: e.id
        )

        # Parto dal primo livello: pacchetto vuoto, durata/costo/valore 0, nessun punto visitato
        self._ricorsione(0, [], 0, 0.0, 0, set())

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        # TODO: è possibile cambiare i parametri formali della funzione se ritenuto opportuno
        # A - ogni pacchetto parziale è già una soluzione valida (i vincoli sono controllati
        # prima di aggiungere un'escursione): se migliora l'ottimo, lo salvo (con una COPIA!)
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()
            self._costo = costo_corrente

        # B - condizione terminale: non serve un if esplicito, quando start_index
        # arriva a len(...) il for sotto non esegue nessuna iterazione e la funzione ritorna.

        # Provo ad aggiungere, una alla volta, le escursioni dalla posizione start_index in poi
        # (partire da start_index evita di generare lo stesso pacchetto in ordini diversi)
        for i in range(start_index, len(self._escursioni_parco)):
            escursione = self._escursioni_parco[i]

            nuova_durata = durata_corrente + escursione.durata_giorni
            nuovo_costo = costo_corrente + escursione.costo

            # C - filtri: rispetto di giorni, budget e assenza di punti di interesse già visitati
            if self._max_giorni is not None and nuova_durata > self._max_giorni:
                continue
            if self._max_budget is not None and nuovo_costo > self._max_budget:
                continue
            if not escursione.punti_interesse.isdisjoint(punti_usati):
                continue

            # D - calcolo parziale: aggiungo l'escursione e i suoi punti di interesse
            voto_escursione = sum(p.voto_visitatori for p in escursione.punti_interesse)
            pacchetto_parziale.append(escursione)
            punti_usati.update(escursione.punti_interesse)

            # E - ricorsione: dall'escursione successiva (i + 1)
            self._ricorsione(i + 1, pacchetto_parziale, nuova_durata, nuovo_costo,
                             valore_corrente + voto_escursione, punti_usati)

            # F - backtracking: annullo la scelta (i punti erano disgiunti da quelli già usati,
            # quindi posso rimuoverli tutti senza toccare quelli delle scelte precedenti)
            punti_usati.difference_update(escursione.punti_interesse)
            pacchetto_parziale.pop()
