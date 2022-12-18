import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'; 
import { faLinkedinIn, faGithub } from '@fortawesome/free-brands-svg-icons';
import style from "./prolink.module.css"

const ProLink = () => {
    return (
        <div className={style.prolink}>
            <FontAwesomeIcon icon={faLinkedinIn}></FontAwesomeIcon>
            <FontAwesomeIcon icon={faGithub}></FontAwesomeIcon>
        </div>
    );
};

export default ProLink;