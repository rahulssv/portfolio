import React from 'react';
import { Container, Row } from 'react-bootstrap';

import './Footer.scss';


function Footer() {
  return (
    <footer>
      <Container>
        <Row className="text-center">
          <p>© {new Date().getFullYear()} -  Developed by <a href="https://github.com/rahulssv">Rahul Vishwakarma</a>. All rights reserved.</p>
        </Row>
      </Container>
    </footer>
  );
}

export default Footer;
