import  Link  from 'next/link';
import { Children } from 'react';



const LinkBtn = ({children, link, className}) => {
    return (
        <button className={className}>
            <Link href={`/${link}`}> {children} </Link>
        </button>
    );
};

export default LinkBtn;