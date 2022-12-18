import React from 'react';
import Navbar from './Navbar';
import style from "./navbar.module.css"





const Headeur = ({scrolled}) => {
    return (
        <header  className={scrolled ? style.header : style.header_scrolled}>
                    <Navbar ></Navbar>
        </header>
    );
};

export default Headeur;