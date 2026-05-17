# EtnoSIG — Contexto Etnológico del Proyecto
## Información de Dominio para el Desarrollador

Este documento contextualiza el dominio del negocio para que el desarrollador que construya el sistema comprenda *qué* procesa y *por qué* cada componente existe.

---

## 1. ¿Qué es un Estudio Etnológico?

Un estudio etnológico es una investigación antropológica que documenta la existencia, identidad cultural, organización y territorio de una comunidad que se reivindica como indígena. En Colombia, este estudio es requisito para que el Estado (a través del **Ministerio del Interior — Dirección de Asuntos Indígenas, Rrom y Minorías [DAIRM]**) reconozca formalmente al grupo como comunidad indígena.

Sin reconocimiento: la comunidad no accede a proyectos del Estado, no puede gestionar tierra ante la Agencia Nacional de Tierras, no obtiene atención diferencial en salud y educación.

**El informe etnológico es el instrumento que convierte décadas de resistencia cultural en reconocimiento jurídico.**

---

## 2. El Caso de Referencia — Cabildo Murui Muina

El primer estudio que procesará el sistema es el del **Cabildo Indígena del Pueblo Muruy-Muina de la Etnia Huitoto**, ubicado en:

| Dato | Valor |
|---|---|
| Municipio | La Montañita, Caquetá |
| Vereda | Semillas de Paz (ETCR Agua Bonita) |
| NIT | 901010837-9 |
| Coordenadas | 1°22′28″N 75°24′00″W |
| Contrato | UC-CPS-MINTERIOR-023-2026 |

### Historia en Tres Frases
1. El clan Jeduia+ (Huitoto) fue el primer poblador de La Montañita. Los colonos y caucheros (desde 1909) los desplazaron de su territorio ancestral de **220.240 hectáreas**.
2. La comunidad se reorganizó jurídicamente en **2016** en apenas **1 hectárea** donada, con 40 familias y ~110 personas.
3. El estudio de la Universidad de Cartagena busca obtener el **registro formal ante el Ministerio del Interior**, primer paso para recuperar derechos.

### Autoridades Actuales (2026)
| Cargo | Nombre | Pueblo |
|---|---|---|
| Gobernadora | Luz Celida Perdomo Pakki | Murui Muina |
| Cacique | Wualdo (Duvoldo) Orozco Ortiz | Coreguaje |
| Vicegobernador | Ancízar Posada Ramos | — |
| Secretaria | Ingri Natalia Perdomo Pakky | Murui Muina |

---

## 3. Las Tres Fases del Estudio — En Detalle

### FASE 1 — Pre-campo (Acervo Documental)
**Qué es:** Toda la documentación que la comunidad tiene sobre sí misma + documentos institucionales.
**Por qué importa en el sistema:** El motor documental extrae los datos de identidad, población, historia y organización de estos archivos.

**Archivos clave y su función en el informe:**

| Archivo | Datos que aporta |
|---|---|
| Solicitud Formal.pdf | Cifras poblacionales que la comunidad declaró al Ministerio |
| Reglamento interno.pdf | Estructura organizativa, cargos, normas de convivencia |
| Acta de elección.pdf | Nombres y cargos de autoridades elegidas |
| Acta de posesión.pdf | Confirmación oficial de autoridades ante alcaldía |
| Reseña histórica.docx | Historia del clan, despojo, reconstitución |
| Autocenso_Murui Muina.xlsx | Censo 2023: 37 familias, 102 personas |
| Autocenso depurado.xlsx | Censo 2026: 14 familias, 31 personas (núcleo activo) |
| CENSO COMUNIDAD 2023.pdf | Versión PDF del censo con datos adicionales |
| bd-caqueta.pdf | Datos DANE del departamento |
| RUT comunidad.pdf | NIT y datos fiscales |
| CC Gobernadora.pdf | Cédula de ciudadanía de la gobernadora |

### FASE 2 — Campo (Trabajo de Campo y SIG)
**Qué es:** Lo que el equipo de investigación levantó en territorio (15-17 de marzo de 2026).
**Por qué importa en el sistema:** El proyecto QGIS/GeoPackage es el insumo central del Motor SIG.

**Archivos clave:**

| Archivo | Datos que aporta |
|---|---|
| ETNIA1_CABILDO_MURUI_MUINA_GRUPO3.qgz | Proyecto QGIS con todas las capas |
| *.gpkg | GeoPackage con capas vectoriales |
| Fichas de Capas (XLSX) | Metadatos de cada punto GPS levantado |
| DIARIO DE CAMPO.pdf | Narrativa etnográfica para la sección de observación |
| FICHA DE COMISIÓN.pdf | Análisis multidimensional (5 dimensiones) |
| Apuntes reuniones.pdf | Datos cualitativos de grupos focales |
| ÁRBOL DE RIESGO.pdf | Amenazas y vulnerabilidades |
| CARTOGRAFÍA SOCIAL.pdf | Mapa comunitario participativo |
| Evidencia fotográfica (JPG/HEIC) | Fotos por categoría cultural |

**Las 5 Dimensiones del Análisis de Campo:**
1. **Subjetiva (Identidad):** Autodenominación, cosmovisión, tipos de afiliación
2. **Intra-organizativa:** Instancias de decisión, cargos, normas internas
3. **Inter-relacional:** Relaciones con instituciones, vecinos, otras comunidades
4. **Prospectiva:** Plan de vida, proyecciones, sueños comunitarios
5. **De Riesgo:** Amenazas, vulnerabilidades, estrategias de mitigación

### FASE 3 — Post-campo (Síntesis e Informe)
**Qué es:** El informe etnológico final + el borrador de resolución del Ministerio.
**Por qué importa en el sistema:** Es la plantilla/referencia de lo que el sistema debe generar.

| Archivo | Función |
|---|---|
| Informe_Comunidad Murui Muina.md | **Plantilla de referencia** — el Word a generar debe replicar esta estructura |
| Borrador Acto administrativo.md | Modelo de resolución — referencia para el acto jurídico |

---

## 4. Marco Jurídico que el Sistema Debe Conocer

El informe cita estas normas. El sistema las incluye automáticamente en la sección de referencias:

| Norma | Relevancia |
|---|---|
| Constitución Política Art. 7, 8 | Reconocimiento de diversidad étnica |
| Constitución Política Art. 246, 330 | Autoridades tradicionales y territorios |
| Convenio 169 OIT (Ley 21/1991) | **Autorreconocimiento como criterio fundamental** |
| Decreto 2164 de 1995 | Dotación y titulación de resguardos |
| Decreto 1071 de 2015 | Reglamentación sector agropecuario y rural |
| Ley 89 de 1890 | Marco legal de cabildos indígenas |
| Sentencias C-169, T-349, SU-510, T-129 (CC) | Jurisprudencia sobre derechos indígenas |

**Principio rector más importante:**
> El autorreconocimiento es el criterio fundamental para determinar la pertenencia a una comunidad indígena (Convenio 169 OIT). El sistema no juzga si la comunidad ES indígena — documenta objetivamente que SE RECONOCE COMO TAL y ejerce prácticas culturales propias.

---

## 5. Los Tres Motivos de Reconocimiento

El acto administrativo de reconocimiento se basa en tres motivos que el sistema debe documentar y validar:

### Motivo 1 — Cohesión de Grupo
El sistema extrae evidencia de:
- Sistema de justicia interna (mambeadero como tribunal)
- Multas por inasistencia ($50.000 COP)
- Cuotas de afiliación ($2.000.000 COP por familia)
- Mecanismos de expulsión
- Asistencia a asambleas

### Motivo 2 — Cosmovisión Propia
El sistema extrae evidencia de:
- Autodenominación ("Gente de Centro", "hijos del tabaco, la coca y la yuca dulce")
- Origen mítico (Kom+mafo, río Igaraparaná)
- Elementos sagrados (Mambe, Mambeadero, Maguaré)
- Prácticas rituales documentadas en campo

### Motivo 3 — Sistema Normativo Propio
El sistema extrae y documenta:
- Estructura de autoridad: Cacique (espiritual), Gobernadora (civil), Abuela Consejera (ética), Médico Tradicional (salud)
- Reglamento interno propio (no derivado de ley estatal)
- Asamblea y mambeadero como instancias de decisión

---

## 6. Conceptos Culturales que Aparecen en los Documentos

El desarrollador encontrará estos términos en los corpus. Esta tabla los contextualiza:

| Término | Significado | Relevancia para el Sistema |
|---|---|---|
| **Mambe / Mambeo** | Preparado de coca. Práctica espiritual y cognitiva | Práctica cultural central — extraer y documentar |
| **Mambeadero** | Espacio sagrado nocturno de deliberación | Aparece como capa SIG y como instancia de gobierno |
| **Maloka/Maloca** | Vivienda comunal sagrada | Infraestructura comunitaria — capa SIG POL |
| **Maguaré** | Instrumento sagrado de comunicación (tambor) | Dato de pérdida cultural — retenido por el Ejército |
| **Chagra** | Huerto tradicional | Capa SIG — zona productiva |
| **Clan Jeduia+** | Linaje específico del pueblo Huitoto | Identificación genealógica de la comunidad |
| **ETCR** | Espacio Territorial de Capacitación y Reincorporación (excombatientes FARC) | Contexto político del territorio |
| **DAIRM** | Dirección de Asuntos Indígenas, Rrom y Minorías | Entidad del Ministerio que registra a la comunidad |
| **ACOTRI** | Asociación Colombiana de Cabildos y Autoridades Tradicionales Indígenas | Organización de apoyo — afiliaron en 2024 |
| **Bajuma/Bajumuna** | Grupo armado ilegal presente en la zona | Dato de riesgo — manejar con confidencialidad |

---

## 7. Sensibilidades Éticas para el Desarrollador

### 7.1 Información de Seguridad
Los documentos contienen información sobre **amenazas de grupos armados** y **extorsión a la Gobernadora**. Esta información:
- Debe manejarse con acceso restringido (solo `admin` y `tecnico`)
- No debe aparecer en logs sin cifrar
- En el informe Word, se incluye en la sección de dimensión de riesgo pero con lenguaje cuidadoso

### 7.2 Datos Personales Sensibles
- Cédulas de identidad de autoridades
- Datos de contacto (teléfonos, emails)
- Información de salud (subregistro del Médico Tradicional)
→ Cifrar en BD, acceso solo por personal autorizado

### 7.3 Fotografías
Las fotografías de personas de la comunidad son material etnográfico sensible:
- No publicar en interfaces públicas
- Solo accesible en el panel privado del responsable técnico
- En el Word final, solo las autorizadas por la comunidad

### 7.4 Propiedad del Informe
El informe generado pertenece al Ministerio del Interior y a la comunidad. El sistema es un asistente técnico, no el autor intelectual.

---

## 8. Variaciones entre Estudios Futuros

El sistema está diseñado para múltiples comunidades. Estas son las variaciones esperadas:

| Aspecto | Murui Muina (caso 1) | Variación esperada |
|---|---|---|
| Número de capas SIG | 4 capas principales fijas | Siempre las mismas 4 capas |
| Radio de buffer | 50 metros | Ajustable por estudio |
| Número de archivos | ~45 archivos | Variable (20-100+) |
| Idioma de documentos | Español | Siempre español |
| Estructura de carpetas Drive | FASE1/FASE2/FASE3 | Estandarizada (no varía) |
| Pueblo indígena | Huitoto (Murui Muina) | Variable — cualquier pueblo |
| Municipio/Departamento | La Montañita, Caquetá | Variable — toda Colombia |
| Número de autoridades | 8 cargos | Variable (5-12) |
| Mezcla intercultural | Murui + Coreguaje | Variable |

---

## 9. Tabla de Correspondencia: Dato → Sección del Informe

| Dato extraído | Sección del Word |
|---|---|
| Nombre comunidad, NIT, municipio | Portada + Sección 1 |
| Familias/personas (todas las fuentes) | Sección 1 + Sección 8 (discrepancias) |
| Historia del clan, origen mítico | Sección 3 (Dimensión subjetiva) |
| Autoridades (cargos + nombres) | Sección 4 (Organigrama) |
| Relaciones institucionales | Sección 5 (Inter-relacional) |
| Capas SIG puntuales | Sección 6 (mapa por capa) |
| Buffers, matrices, superposiciones | Sección 7 (análisis integrado) |
| Árbol de riesgo | Sección 12 |
| Evidencia fotográfica | Sección 11 |
| Línea de tiempo | Sección 10 |
| Marco jurídico | Sección 13 + Sección 14 |
| Concepto favorable | Sección 13 |
