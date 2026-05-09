--
-- PostgreSQL database dump
--

\restrict cFHzBoFMfB0Pt2SaLqtKWoMdoHPvAOTykaIwwFYgrbmGuGXWvAEceFu3hj9ph4P

-- Dumped from database version 15.17
-- Dumped by pg_dump version 15.17

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

--
-- Name: orderstatus; Type: TYPE; Schema: public; Owner: cookie_user
--

CREATE TYPE public.orderstatus AS ENUM (
    'PENDING',
    'CONFIRMED',
    'PAID',
    'DELIVERED',
    'REJECTED'
);


ALTER TYPE public.orderstatus OWNER TO cookie_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: cookie_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO cookie_user;

--
-- Name: order_items; Type: TABLE; Schema: public; Owner: cookie_user
--

CREATE TABLE public.order_items (
    id integer NOT NULL,
    order_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer NOT NULL,
    unit_price double precision NOT NULL,
    product_name character varying(100)
);


ALTER TABLE public.order_items OWNER TO cookie_user;

--
-- Name: order_items_id_seq; Type: SEQUENCE; Schema: public; Owner: cookie_user
--

CREATE SEQUENCE public.order_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.order_items_id_seq OWNER TO cookie_user;

--
-- Name: order_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cookie_user
--

ALTER SEQUENCE public.order_items_id_seq OWNED BY public.order_items.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: cookie_user
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    customer_instagram character varying NOT NULL,
    delivery_date timestamp without time zone NOT NULL,
    description character varying NOT NULL,
    reference_photos character varying[],
    status public.orderstatus NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    amount_paid double precision NOT NULL,
    total_amount double precision NOT NULL
);


ALTER TABLE public.orders OWNER TO cookie_user;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: cookie_user
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.orders_id_seq OWNER TO cookie_user;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cookie_user
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: cookie_user
--

CREATE TABLE public.products (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    price double precision NOT NULL,
    image_url character varying(255),
    is_active boolean NOT NULL
);


ALTER TABLE public.products OWNER TO cookie_user;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: cookie_user
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_id_seq OWNER TO cookie_user;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cookie_user
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: order_items id; Type: DEFAULT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.order_items ALTER COLUMN id SET DEFAULT nextval('public.order_items_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: cookie_user
--

COPY public.alembic_version (version_num) FROM stdin;
ae74e273134e
\.


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: public; Owner: cookie_user
--

COPY public.order_items (id, order_id, product_id, quantity, unit_price, product_name) FROM stdin;
1	1	1	12	1200	\N
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: cookie_user
--

COPY public.orders (id, customer_instagram, delivery_date, description, reference_photos, status, created_at, amount_paid, total_amount) FROM stdin;
1	Sofyy.te 	2026-07-15 00:00:00	Que quede lindo 	\N	PENDING	2026-05-09 01:17:23.286912	10000	14400
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: cookie_user
--

COPY public.products (id, name, description, price, image_url, is_active) FROM stdin;
1	Galleta individual	Tamaño: 8 cm	1200	/media/products/ae273b0f0dfa467680d8b7cfe7cab5ad.jpg	t
2	Caja S	Tamaño: 6 cm. Hasta 6 diseños.	7500	/media/products/9b0d35b44ebc4c9ba86933daed367f80.jpg	t
3	Caja M	Tamaño: 6 cm. Hasta 7 diseños.	9000	/media/products/c7d27cadf2ab4c569e77ee947d25df25.jpg	t
\.


--
-- Name: order_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cookie_user
--

SELECT pg_catalog.setval('public.order_items_id_seq', 1, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cookie_user
--

SELECT pg_catalog.setval('public.orders_id_seq', 1, true);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cookie_user
--

SELECT pg_catalog.setval('public.products_id_seq', 3, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: ix_order_items_id; Type: INDEX; Schema: public; Owner: cookie_user
--

CREATE INDEX ix_order_items_id ON public.order_items USING btree (id);


--
-- Name: ix_orders_id; Type: INDEX; Schema: public; Owner: cookie_user
--

CREATE INDEX ix_orders_id ON public.orders USING btree (id);


--
-- Name: ix_products_id; Type: INDEX; Schema: public; Owner: cookie_user
--

CREATE INDEX ix_products_id ON public.products USING btree (id);


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cookie_user
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- PostgreSQL database dump complete
--

\unrestrict cFHzBoFMfB0Pt2SaLqtKWoMdoHPvAOTykaIwwFYgrbmGuGXWvAEceFu3hj9ph4P

