import React from 'react';
import Navbar from './NavbarFade';
import Logo from '../components/Logo';




const Headeur = ({scrolled}) => {
    return (
        <div  className={scrolled ? "navandcontact scrolled" : "navandcontact"}>
                    <Logo></Logo>
                    <Navbar ></Navbar>
        </div>
    );
};

export default Headeur;