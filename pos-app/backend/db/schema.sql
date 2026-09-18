-- 設計仕様書 6.3 テーブル定義（MySQL 8 / Azure Database for MySQL Flexible Server）
-- 文字コード utf8mb4（DB-5）。日時は UTC で保存（DB-4）。
CREATE DATABASE IF NOT EXISTS pos CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE pos;

CREATE TABLE IF NOT EXISTS staff (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  login_id      VARCHAR(32) COLLATE utf8mb4_bin NOT NULL,
  password_hash VARCHAR(60) NOT NULL,
  name          VARCHAR(50) NOT NULL,
  created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_staff_login_id (login_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  product_code VARCHAR(13) COLLATE utf8mb4_bin NOT NULL,
  name         VARCHAR(100) NOT NULL,
  unit_price   INT NOT NULL,
  created_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_products_code (product_code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS members (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  member_code VARCHAR(32) COLLATE utf8mb4_bin NOT NULL,
  name        VARCHAR(50) NOT NULL,
  phone       VARCHAR(20) NULL,
  address     VARCHAR(200) NULL,
  gender      VARCHAR(10) NULL,
  age         INT NULL,
  created_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_members_code (member_code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tax_rates (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  rate       DECIMAL(5,2) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS discounts (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id     BIGINT UNSIGNED NOT NULL,
  start_date     DATE NOT NULL,
  end_date       DATE NOT NULL,
  discount_type  VARCHAR(10) NOT NULL,
  discount_value DECIMAL(10,2) NOT NULL,
  created_at     DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at     DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  CONSTRAINT fk_discounts_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
  CONSTRAINT ck_discounts_period CHECK (end_date >= start_date),
  CONSTRAINT ck_discounts_type CHECK (discount_type IN ('percent', 'amount'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
  id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  transacted_at     DATETIME(6) NOT NULL,
  staff_id          BIGINT UNSIGNED NOT NULL,
  member_id         BIGINT UNSIGNED NULL,
  subtotal_excl_tax INT NOT NULL,
  tax_amount        INT NOT NULL,
  total_incl_tax    INT NOT NULL,
  created_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  CONSTRAINT fk_transactions_staff  FOREIGN KEY (staff_id)  REFERENCES staff(id)   ON DELETE RESTRICT,
  CONSTRAINT fk_transactions_member FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transaction_items (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  transaction_id  BIGINT UNSIGNED NOT NULL,
  line_no         INT NOT NULL,
  product_id      BIGINT UNSIGNED NOT NULL,
  unit_price      INT NOT NULL,
  quantity        INT NOT NULL,
  discount_amount INT NOT NULL DEFAULT 0,
  line_total      INT NOT NULL,
  created_at      DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_transaction_items_line (transaction_id, line_no),
  CONSTRAINT fk_items_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_items_product     FOREIGN KEY (product_id)     REFERENCES products(id)     ON DELETE RESTRICT,
  CONSTRAINT ck_transaction_items_quantity CHECK (quantity BETWEEN 1 AND 99)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS discount_applications (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  transaction_item_id BIGINT UNSIGNED NOT NULL,
  discount_id         BIGINT UNSIGNED NOT NULL,
  applied_amount      INT NOT NULL,
  created_at          DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  CONSTRAINT fk_app_item     FOREIGN KEY (transaction_item_id) REFERENCES transaction_items(id) ON DELETE RESTRICT,
  CONSTRAINT fk_app_discount FOREIGN KEY (discount_id)         REFERENCES discounts(id)         ON DELETE RESTRICT
) ENGINE=InnoDB;
