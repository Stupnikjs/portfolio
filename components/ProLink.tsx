import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faGithub } from '@fortawesome/free-brands-svg-icons';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import style from './prolink.module.css'
import { faEnvelope } from '@fortawesome/free-solid-svg-icons';


const Prolink = () => {
    const [offset, setOffset] = useState(10)

    useEffect(()=> {

    const timer = () => {
        setInterval(()=> {
            setOffset( offset + 1)
            console.log("hello")
        }, 1000)
    }
    
    

    }, [offset])

    return (
        <div className={style.prolink} style={{marginLeft: `${offset}px`}}>
            <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faGithub}/> </Link>
            <Link href="mailto:n.boudier.ph@gmail.com"> <FontAwesomeIcon icon={faEnvelope}/> </Link>
        </div>
    );
};

export default Prolink;