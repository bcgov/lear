--
-- PostgreSQL database dump
--

-- Dumped from database version 11.11 (Debian 11.11-1.pgdg90+1)
-- Dumped by pg_dump version 13.2

-- Started on 2021-06-24 07:45:30 PDT

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_with_oids = false;

CREATE USER "userA7C" with SUPERUSER;
CREATE DATABASE tracker OWNER "userA7C";
\c tracker
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET search_path=tracker;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 196 (class 1259 OID 283323)
-- Name: alembic_version; Type: TABLE; Schema: public;  Owner: userA7C
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO "userA7C";

--
-- TOC entry 198 (class 1259 OID 283330)
-- Name: message_processing; Type: TABLE; Schema: public;  Owner: userA7C
--

CREATE TABLE public.message_processing (
                                           id integer NOT NULL,
                                           source character varying(36),
                                           message_id character varying(60) NOT NULL,
                                           identifier character varying(36),
                                           message_type character varying(35) NOT NULL,
                                           status character varying(10) NOT NULL,
                                           message_json jsonb NOT NULL,
                                           message_seen_count integer NOT NULL,
                                           last_error character varying(1000),
                                           create_date timestamp with time zone NOT NULL,
                                           last_update timestamp with time zone NOT NULL
);


ALTER TABLE public.message_processing OWNER TO "userA7C";

--
-- TOC entry 197 (class 1259 OID 283328)
-- Name: message_processing_id_seq; Type: SEQUENCE; Schema: public;  Owner: userA7C
--

CREATE SEQUENCE public.message_processing_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.message_processing_id_seq OWNER TO "userA7C";

--
-- TOC entry 2883 (class 0 OID 0)
-- Dependencies: 197
-- Name: message_processing_id_seq; Type: SEQUENCE OWNED BY; Schema: public;  Owner: userA7C
--

ALTER SEQUENCE public.message_processing_id_seq OWNED BY public.message_processing.id;


--
-- TOC entry 2745 (class 2604 OID 283333)
-- Name: message_processing id; Type: DEFAULT; Schema: public;  Owner: userA7C
--

ALTER TABLE ONLY public.message_processing ALTER COLUMN id SET DEFAULT nextval('public.message_processing_id_seq'::regclass);


--
-- TOC entry 2875 (class 0 OID 283323)
-- Dependencies: 196
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public;  Owner: userA7C
--

COPY public.alembic_version (version_num) FROM stdin;
786dac4b44ef
\.


--
-- TOC entry 2877 (class 0 OID 283330)
-- Dependencies: 198
-- Data for Name: message_processing; Type: TABLE DATA; Schema: public;  Owner: userA7C
--

COPY public.message_processing (id, source, message_id, identifier, message_type, status, message_json, message_seen_count, last_error, create_date, last_update) FROM stdin;
\.


--
-- TOC entry 2884 (class 0 OID 0)
-- Dependencies: 197
-- Name: message_processing_id_seq; Type: SEQUENCE SET; Schema: public;  Owner: userA7C
--

SELECT pg_catalog.setval('public.message_processing_id_seq', 1, false);


--
-- TOC entry 2747 (class 2606 OID 283327)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public;  Owner: userA7C
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- TOC entry 2753 (class 2606 OID 283338)
-- Name: message_processing message_processing_pkey; Type: CONSTRAINT; Schema: public;  Owner: userA7C
--

ALTER TABLE ONLY public.message_processing
    ADD CONSTRAINT message_processing_pkey PRIMARY KEY (id);


--
-- TOC entry 2748 (class 1259 OID 283339)
-- Name: ix_message_processing_identifier; Type: INDEX; Schema: public;  Owner: userA7C
--

CREATE INDEX ix_message_processing_identifier ON public.message_processing USING btree (identifier);


--
-- TOC entry 2749 (class 1259 OID 283340)
-- Name: ix_message_processing_message_id; Type: INDEX; Schema: public;  Owner: userA7C
--

CREATE UNIQUE INDEX ix_message_processing_message_id ON public.message_processing USING btree (message_id);


--
-- TOC entry 2750 (class 1259 OID 283341)
-- Name: ix_message_processing_message_type; Type: INDEX; Schema: public;  Owner: userA7C
--

CREATE INDEX ix_message_processing_message_type ON public.message_processing USING btree (message_type);


--
-- TOC entry 2751 (class 1259 OID 283342)
-- Name: ix_message_processing_status; Type: INDEX; Schema: public;  Owner: userA7C
--

CREATE INDEX ix_message_processing_status ON public.message_processing USING btree (status);


-- Completed on 2021-06-24 07:45:33 PDT

--
-- PostgreSQL database dump complete
--

