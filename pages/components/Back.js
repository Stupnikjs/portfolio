import React from 'react';
import Link from 'next/link';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChevronLeft } from '@fortawesome/free-solid-svg-icons';

const Back = () => {
    return (
        <Link className='back' href="/"><FontAwesomeIcon icon={faChevronLeft}></FontAwesomeIcon></Link>
    );
};

export default Back;