import React from 'react';
import Navbar from './Navbar';
import Logo from '../components/Logo';
/* font awsome + react a maitriser */


const Headeur = () => {
    return (
       <div className='headeur'>    
        <Logo id={"navLogo"}></Logo>
        <Navbar></Navbar> 
       </div> 
    );
};

export default Headeur;