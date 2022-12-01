import React from 'react';
import  Link  from "next/link";


const Navbar = () => {
    return (
        <nav className='navbar'>
            <Link   href='/about' > 01. À Propos </Link>
            <Link   href='/experience' > 02. Experience </Link>        
            <Link   href='/curriculum' >03. Mon CV</Link>    
            <Link href='/contact'> 04. Contact</Link>    
        </nav>
        
    );
};

export default Navbar;