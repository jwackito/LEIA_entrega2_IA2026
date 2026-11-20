# Correlativas — Licenciatura en Informática (UNLP)

**Plan:** 2021  
**Fuente:** [Facultad de Informática UNLP — Licenciatura en Informática, Plan 2021](https://www.info.unlp.edu.ar/licenciatura-en-informatica-plan-2021/)

Convención del grafo: `A --> B` significa que **A es correlativa de B**, es decir, para cursar B necesitás A. Se usa la columna **Correlativas** del plan oficial. El plan no distingue acá entre cursar y rendir el final; no se duplican las aristas.

## Grafo

```mermaid
flowchart LR
  subgraph Y1["1er año"]
    CNE["CNE · Expresión de Problemas y Algoritmos"]
    CNC["CNC · Conceptos de Organización de Computadoras"]
    CNM["CNM · Matemática 0"]
    SI106["SI106 · Conceptos de Algoritmos, Datos y Programas"]
    SI104["SI104 · Organización de Computadoras"]
    SI101["SI101 · Matemática 1"]
    SI107["SI107 · Taller de Programación"]
    SI105["SI105 · Arquitectura de Computadoras"]
    SI102["SI102 · Matemática 2"]
  end

  subgraph Y2["2do año"]
    SI209["SI209 · Fundamentos de Organización de Datos"]
    SI203["SI203 · Algoritmos y Estructuras de Datos"]
    SI207["SI207 · Seminario de Lenguajes"]
    SI210["SI210 · Diseño de Bases de Datos"]
    SI202["SI202 · Ingeniería de Software 1"]
    SI206["SI206 · Orientación a Objetos 1"]
    SI204["SI204 · Introducción a los Sistemas Operativos"]
    SI208["SI208 · Taller de lecto-comprensión y Traducción en Inglés"]
  end

  subgraph Y3["3er año"]
    SI308["SI308 · Matemática 3"]
    SI302["SI302 · Ingeniería de Software 2"]
    SI306["SI306 · Conceptos y Paradigmas de Lenguajes de Programación"]
    SI307["SI307 · Orientación a Objetos 2"]
    SI304["SI304 · Redes y Comunicaciones"]
    SI301["SI301 · Programación Concurrente"]
    SI305["SI305 · Proyecto de Software"]
    I309["0I309 · Computabilidad y Complejidad"]
  end

  subgraph Y4["4to año"]
    I401["0I401 · Teoría de la Computación y Verificación de Programas"]
    SI403["SI403 · Sistemas Operativos"]
    I404["0I404 · Sistemas Paralelos"]
    OPT["Optativa 1 LI"]
    I406["0I406 · Lógica e Inteligencia Artificial"]
    SI409["SI409 · Matemática 4"]
    I402["0I402 · Laboratorio de Software"]
    I405["0I405 · Programación Distribuida y Tiempo Real"]
  end

  subgraph Y5["5to año"]
    I502["0I502 · Diseño de Experiencia de Usuario"]
    SI504["SI504 · Aspectos Sociales y Profesionales de Informática"]
    SI505["SI505 · Aspectos Éticos, Sociales y Profesionales Avanzados de Informática"]
    I503["0I503 · Tesina de Licenciatura en Informática"]
  end

  CNE --> SI106
  CNC --> SI104
  CNM --> SI101
  SI106 --> SI107
  SI104 --> SI105
  SI101 --> SI102

  SI107 --> SI209
  SI102 --> SI203
  SI107 --> SI203
  SI107 --> SI207
  SI209 --> SI210
  SI107 --> SI202
  SI107 --> SI206
  SI107 --> SI204
  SI105 --> SI204

  SI102 --> SI308
  SI202 --> SI302
  SI208 --> SI302
  SI203 --> SI306
  SI207 --> SI306
  SI208 --> SI306
  SI206 --> SI307
  SI208 --> SI307
  SI102 --> SI304
  SI204 --> SI304
  SI208 --> SI304
  SI204 --> SI301
  SI207 --> SI301
  SI208 --> SI301
  SI210 --> SI305
  SI202 --> SI305
  SI203 --> SI305
  SI206 --> SI305
  SI207 --> SI305
  SI208 --> SI305
  SI203 --> I309
  SI308 --> I309
  SI208 --> I309

  SI308 --> I401
  SI306 --> I401
  SI304 --> SI403
  SI301 --> I404
  SI102 --> I406
  SI306 --> I406
  SI308 --> SI409
  SI305 --> I402
  SI306 --> I405
  SI304 --> I405

  SI302 --> I502
  I402 --> I502
  SI305 --> SI504
  SI305 --> SI505
```

## Correlativas por materia

| Año | Código | Materia | Requiere |
|---|---|---|---|
| 1 | CNE | Expresión de Problemas y Algoritmos | — |
| 1 | CNC | Conceptos de Organización de Computadoras | — |
| 1 | CNM | Matemática 0 | — |
| 1 | SI106 | Conceptos de Algoritmos, Datos y Programas | CNE |
| 1 | SI104 | Organización de Computadoras | CNC |
| 1 | SI101 | Matemática 1 | CNM |
| 1 | SI107 | Taller de Programación | SI106 |
| 1 | SI105 | Arquitectura de Computadoras | SI104 |
| 1 | SI102 | Matemática 2 | SI101 |
| 2 | SI209 | Fundamentos de Organización de Datos | SI107 |
| 2 | SI203 | Algoritmos y Estructuras de Datos | SI102, SI107 |
| 2 | SI207 | Seminario de Lenguajes | SI107 |
| 2 | SI210 | Diseño de Bases de Datos | SI209 |
| 2 | SI202 | Ingeniería de Software 1 | SI107 |
| 2 | SI206 | Orientación a Objetos 1 | SI107 |
| 2 | SI204 | Introducción a los Sistemas Operativos | SI107, SI105 |
| 2 | SI208 | Taller de lecto-comprensión y Traducción en Inglés | — |
| 3 | SI308 | Matemática 3 | SI102 |
| 3 | SI302 | Ingeniería de Software 2 | SI202, SI208 |
| 3 | SI306 | Conceptos y Paradigmas de Lenguajes de Programación | SI203, SI207, SI208 |
| 3 | SI307 | Orientación a Objetos 2 | SI206, SI208 |
| 3 | SI304 | Redes y Comunicaciones | SI102, SI204, SI208 |
| 3 | SI301 | Programación Concurrente | SI204, SI207, SI208 |
| 3 | SI305 | Proyecto de Software | SI210, SI202, SI203, SI206, SI207, SI208 |
| 3 | 0I309 | Computabilidad y Complejidad | SI203, SI308, SI208 |
| 4 | 0I401 | Teoría de la Computación y Verificación de Programas | SI308, SI306 |
| 4 | SI403 | Sistemas Operativos | SI304 |
| 4 | 0I404 | Sistemas Paralelos | SI301 |
| 4 | — | Optativa 1 LI | Según la optativa elegida |
| 4 | 0I406 | Lógica e Inteligencia Artificial | SI102, SI306 |
| 4 | SI409 | Matemática 4 | SI308 |
| 4 | 0I402 | Laboratorio de Software | SI305 |
| 4 | 0I405 | Programación Distribuida y Tiempo Real | SI306, SI304 |
| 5 | 0I502 | Diseño de Experiencia de Usuario | SI302, 0I402 |
| 5 | SI504 | Aspectos Sociales y Profesionales de Informática | SI305 |
| 5 | SI505 | Aspectos Éticos, Sociales y Profesionales Avanzados de Informática | SI305 |
| 5 | 0I503 | Tesina de Licenciatura en Informática | Regla especial: todos los finales de 1º y 2º año + 2 finales más |

## Notas

- **0I503 Tesina:** no se puede expresar como aristas simples. Requiere tener aprobados todos los exámenes finales de 1º y 2º año y al menos 2 exámenes finales más.
- **Optativa 1 LI:** no tiene correlativas fijas; depende de la optativa que se elija. Por eso queda aislada en el grafo.
- El plan oficial escribe `OI402` (letra O) en la correlativa de `0I502`; acá se normaliza a `0I402` (cero).
- Si este grafo se usa como seed de la app, `0I503` y la optativa necesitan un tratamiento aparte: el modelo actual de correlativas solo admite pares materia → correlativa.
