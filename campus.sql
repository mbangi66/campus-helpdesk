-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema campus
-- -----------------------------------------------------
DROP SCHEMA IF EXISTS `campus` ;

-- -----------------------------------------------------
-- Schema campus
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `campus` DEFAULT CHARACTER SET utf8 ;
USE `campus` ;

-- -----------------------------------------------------
-- Table `campus`.`users`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `campus`.`users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(45) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('student','agent','admin') NOT NULL DEFAULT 'student',
  `created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `user_name_UNIQUE` (`username` ASC) VISIBLE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `campus`.`tickets`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `campus`.`tickets` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `category` VARCHAR(100) NOT NULL,
  `status` VARCHAR(60) NOT NULL DEFAULT 'open',
  `created_at` TIMESTAMP NOT NULL DEFAULT  CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `user.id_idx` (`user_id` ASC) VISIBLE,
  CONSTRAINT `user.id`
    FOREIGN KEY (`user_id`)
    REFERENCES `campus`.`users` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `campus`.`KnowledgeBase`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `campus`.`KnowledgeBase` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `content` TEXT NOT NULL,
  `category` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `campus`.`comments`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `campus`.`comments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `ticket_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `content` TEXT NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT  CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `ticket.id_idx` (`ticket_id` ASC) VISIBLE,
  INDEX `user.id_idx` (`user_id` ASC) VISIBLE,
  CONSTRAINT `fk_comments_ticket_id`
    FOREIGN KEY (`ticket_id`)
    REFERENCES `campus`.`tickets` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_comments_user_id`
    FOREIGN KEY (`user_id`)
    REFERENCES `campus`.`users` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
